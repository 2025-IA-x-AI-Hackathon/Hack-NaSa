"""
macOS 시스템 Bluetooth + 범용 미디어 제어 + 배터리 정보 조회

하이브리드 접근:
- 시스템 블루투스 (blueutil): 연결/해제, 안정적인 오디오 제어
- BleakClient: 배터리 정보 조회 (GATT 프로토콜)
- nowplayingctl: 범용 미디어 제어

필수 도구 설치:
    brew install blueutil
    brew install switchaudio-osx
    brew install nowplaying-cli
"""

import asyncio
import subprocess
import sys
import json
import os
from typing import List, Dict, Optional
from bleak import BleakScanner, BleakClient


class BluetoothHybridManager:
    """macOS 시스템 Bluetooth + 범용 미디어 제어 + 배터리 정보 클래스"""
    
    def __init__(self):
        self.known_devices_file = "bluetooth_devices.json"
        self.known_devices: Dict[str, str] = self.load_known_devices()
        self.check_dependencies()
    
    def check_dependencies(self):
        """필요한 시스템 도구가 설치되어 있는지 확인"""
        tools = [
            "blueutil",
            "SwitchAudioSource",
            "nowplaying-cli"
        ]
        
        missing = []
        for tool in tools:
            result = subprocess.run(
                ["which", tool],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                missing.append(f"❌ {tool}")
        
        if missing:
            print("⚠️  필수 도구가 설치되어 있지 않습니다:")
            for msg in missing:
                print(msg)
            print("\n설치 후 다시 실행해주세요.")
            sys.exit(1)
        else:
            print("✅ 필수 도구 확인 완료")
    
    def load_known_devices(self) -> Dict[str, str]:
        """저장된 장치 목록 로드"""
        if os.path.exists(self.known_devices_file):
            try:
                with open(self.known_devices_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_known_devices(self):
        """장치 목록 저장"""
        try:
            with open(self.known_devices_file, 'w') as f:
                json.dump(self.known_devices, f, indent=2)
        except Exception as e:
            print(f"⚠️  장치 목록 저장 실패: {e}")
    
    def get_paired_devices(self) -> List[Dict[str, str]]:
        """macOS에 페어링된 Bluetooth 장치 목록"""
        try:
            result = subprocess.run(
                ["blueutil", "--paired"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            devices = []
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split(',')
                        address = None
                        name = "Unknown"
                        connected = False
                        
                        for part in parts:
                            part = part.strip()
                            if part.startswith('address:'):
                                address = part.split(':')[1].strip()
                            elif 'name:' in part:
                                name = part.split('name:')[1].strip().strip('"')
                            elif 'connected' in part and 'not' not in part:
                                connected = True
                        
                        if address:
                            devices.append({
                                'address': address,
                                'name': name,
                                'connected': connected
                            })
            
            return devices
            
        except Exception as e:
            print(f"❌ 페어링된 장치 확인 실패: {e}")
            return []
    
    async def scan_ble_devices(self, timeout: float = 5.0) -> List[Dict[str, str]]:
        """BLE 장치 스캔"""
        try:
            print(f"🔍 BLE 장치 스캔 중 ({timeout}초)...")
            
            devices = []
            async with BleakScanner() as scanner:
                await asyncio.sleep(timeout)
                discovered = scanner.discovered_devices_and_advertisement_data
                
                for address, (device, adv_data) in discovered.items():
                    if adv_data.rssi > -70:
                        name = device.name or "Unknown BLE Device"
                        devices.append({
                            'address': address,
                            'name': name,
                            'connected': False,
                            'type': 'BLE'
                        })
            
            return devices
            
        except Exception as e:
            print(f"❌ BLE 스캔 실패: {e}")
            return []
    
    async def scan_all_devices(self) -> List[Dict[str, str]]:
        """
        페어링된 장치 + BLE 스캔 결과 통합
        모든 장치의 MAC 주소와 BLE UUID를 매칭
        """
        print("\n" + "=" * 80)
        print("📱 Bluetooth 장치 검색 중...")
        print("=" * 80)
        
        # 1. 페어링된 장치 조회 (MAC 주소)
        paired = self.get_paired_devices()
        print(f"   페어링된 장치: {len(paired)}개")
        
        # 2. BLE 스캔 (더 긴 시간, 더 많은 장치 발견)
        ble_devices = await self.scan_ble_devices(timeout=5.0)
        print(f"   BLE 장치: {len(ble_devices)}개")
        
        # 3. 장치 매칭 (이름으로 매칭)
        ble_by_name = {}
        
        for ble_dev in ble_devices:
            name_key = ble_dev['name'].lower()
            
            # 같은 이름의 BLE 장치가 여러 개면 리스트로 저장
            if name_key not in ble_by_name:
                ble_by_name[name_key] = []
            ble_by_name[name_key].append(ble_dev)
        
        all_devices = []
        processed_ble_addresses = set()
        
        # 4. 페어링된 장치에 BLE UUID 매칭
        print(f"\n   매칭 중...")
        for device in paired:
            name_key = device['name'].lower()
            
            # 방법 1: 이름으로 매칭
            if name_key in ble_by_name:
                ble_matches = ble_by_name[name_key]
                if len(ble_matches) == 1:
                    # 유일한 매칭
                    device['ble_address'] = ble_matches[0]['address']
                    processed_ble_addresses.add(ble_matches[0]['address'].lower())
                    print(f"   ✅ {device['name']}: MAC={device['address']}, BLE={device['ble_address']}")
                elif len(ble_matches) > 1:
                    # 여러 개 매칭됨 (좌/우 이어폰 등)
                    device['ble_address'] = ble_matches[0]['address']
                    device['ble_addresses_all'] = [m['address'] for m in ble_matches]
                    for match in ble_matches:
                        processed_ble_addresses.add(match['address'].lower())
                    print(f"   ✅ {device['name']}: MAC={device['address']}, BLE={device['ble_addresses_all']}")
            else:
                print(f"   ⚪ {device['name']}: MAC={device['address']}, BLE=없음")
            
            all_devices.append(device)
        
        # 5. BLE 전용 장치 추가 (페어링 안 된 것들)
        for ble_dev in ble_devices:
            if ble_dev['address'].lower() not in processed_ble_addresses:
                all_devices.append(ble_dev)
        
        print(f"\n   총 {len(all_devices)}개 장치 발견")
        return all_devices
    
    def connect_device_system(self, address: str, name: str = "Unknown") -> bool:
        """
        macOS 시스템 Bluetooth로 장치 연결 (오디오용)
        UUID 형식이면 시스템 연결은 실패하지만 BLE GATT는 사용 가능
        """
        try:
            # UUID 형식인 경우 (BLE 전용 장치)
            if "-" in address and len(address) == 36:
                print(f"\n⚠️  '{name}'는 BLE 전용 장치입니다.")
                print("   시스템 블루투스 연결은 불가능하지만, GATT 기능(배터리 읽기 등)은 사용 가능합니다.")
                # GATT는 사용 가능하므로 장치 목록에는 추가
                self.known_devices[address] = name
                self.save_known_devices()
                return True  # GATT 용도로는 사용 가능
            
            print(f"\n📱 '{name}' 시스템 블루투스 연결 중...")
            
            result = subprocess.run(
                ["blueutil", "--connect", address],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"✅ '{name}' 시스템 연결 성공!")
                
                self.known_devices[address] = name
                self.save_known_devices()
                
                import time
                time.sleep(2)
                
                return True
            else:
                print(f"❌ 시스템 연결 실패: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 시스템 연결 중 오류: {e}")
            return False
    
    
    def disconnect_device_system(self, address: str, name: str = "Unknown") -> bool:
        """시스템 블루투스 연결 해제"""
        try:
            print(f"\n🔌 '{name}' 시스템 연결 해제 중...")
            
            result = subprocess.run(
                ["blueutil", "--disconnect", address],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"✅ '{name}' 시스템 연결 해제 완료")
                return True
            else:
                print(f"❌ 시스템 연결 해제 실패: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 시스템 연결 해제 중 오류: {e}")
            return False
    
    
    def get_audio_devices(self) -> List[str]:
        """사용 가능한 오디오 출력 장치 목록"""
        try:
            result = subprocess.run(
                ["SwitchAudioSource", "-a", "-t", "output"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                devices = [d.strip() for d in result.stdout.strip().split('\n') if d.strip()]
                return devices
            return []
            
        except Exception as e:
            print(f"❌ 오디오 장치 목록 조회 실패: {e}")
            return []
    
    def switch_audio_output(self, device_name: str) -> bool:
        """오디오 출력을 특정 장치로 전환"""
        try:
            print(f"\n🔊 오디오 출력을 '{device_name}'로 전환 중...")
            
            result = subprocess.run(
                ["SwitchAudioSource", "-s", device_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                print("✅ 오디오 출력 전환 완료")
                return True
            else:
                print("❌ 오디오 출력 전환 실패")
                return False
                
        except Exception as e:
            print(f"❌ 오디오 출력 전환 중 오류: {e}")
            return False
    
    def get_now_playing_info(self) -> Optional[str]:
        """현재 재생 중인 미디어 정보 조회"""
        try:
            result = subprocess.run(
                ["nowplaying-cli", "get", "title", "artist", "album"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return None
            
        except Exception:
            return None
    
    def media_play_pause(self) -> bool:
        """
        미디어 재생/일시정지
        모든 앱(Spotify, YouTube, Netflix, Safari, Chrome 등) 지원
        """
        try:
            print("▶️⏸️  미디어 재생/일시정지...")
            
            # nowplaying-cli 사용 (범용)
            result = subprocess.run(
                ["nowplaying-cli", "togglePlayPause"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("✅ 재생/일시정지 완료")
                return True
            
            print("⚠️  미디어 제어 실패")
            return False
            
        except Exception as e:
            print(f"❌ 미디어 제어 실패: {e}")
            return False
    
    def media_next(self) -> bool:
        """다음 트랙"""
        try:
            print("⏭️  다음 트랙...")
            
            result = subprocess.run(
                ["nowplaying-cli", "next"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("✅ 다음 트랙")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ 다음 트랙 실패: {e}")
            return False
    
    def media_previous(self) -> bool:
        """이전 트랙"""
        try:
            print("⏮️  이전 트랙...")
            
            result = subprocess.run(
                ["nowplaying-cli", "previous"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("✅ 이전 트랙")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ 이전 트랙 실패: {e}")
            return False
    
    def media_info(self) -> bool:
        """현재 재생 중인 미디어 정보 표시"""
        try:
            print("\n🎵 현재 재생 중:")
            print("=" * 80)
            
            # 제목
            result = subprocess.run(
                ["nowplaying-cli", "get", "title"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                print(f"제목: {result.stdout.strip()}")
            
            # 아티스트
            result = subprocess.run(
                ["nowplaying-cli", "get", "artist"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                print(f"아티스트: {result.stdout.strip()}")
            
            # 앨범
            result = subprocess.run(
                ["nowplaying-cli", "get", "album"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                print(f"앨범: {result.stdout.strip()}")
            
            # 재생 상태
            result = subprocess.run(
                ["nowplaying-cli", "get", "playbackRate"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                rate = result.stdout.strip()
                status = "▶️ 재생 중" if rate != "0" else "⏸️ 일시정지"
                print(f"상태: {status}")
            
            print("=" * 80)
            return True
            
        except Exception as e:
            print(f"❌ 정보 조회 실패: {e}")
            return False
    
    # ==================== GATT 읽기/쓰기 기능 ====================
    
    async def read_gatt_characteristic(self, address: str, uuid: str, name: str = "Unknown", ble_address: Optional[str] = None, is_connected: bool = False) -> Optional[bytes]:
        """
        특정 UUID의 GATT 특성(Characteristic) 읽기
        
        Args:
            address: 장치 주소 (MAC)
            uuid: 읽을 특성의 UUID (예: "00002a19-0000-1000-8000-00805f9b34fb")
            name: 장치 이름
            ble_address: BLE UUID
            is_connected: 시스템에 연결되어 있는지 여부
        
        Returns:
            읽은 데이터 (bytes) 또는 None
        """
        try:
            print(f"\n📖 {name}에서 UUID {uuid} 읽기 시도...")
            
            # BLE UUID 필수
            if not ble_address:
                print("❌ BLE UUID가 없어 GATT 연결을 할 수 없습니다.")
                print("   💡 'gatt' 명령어는 BLE UUID가 있는 장치만 사용 가능합니다.")
                return None
            
            print(f"   BLE 주소: {ble_address}")
            
            # 시스템에 연결되어 있으면 먼저 해제
            if is_connected:
                print("⚠️  장치가 시스템에 연결되어 있습니다.")
                print("   GATT 연결을 위해 시스템 연결을 일시적으로 해제합니다...")
                self.disconnect_device_system(address, name)
                await asyncio.sleep(2)
            
            # GATT 연결
            print("   BleakClient로 연결 시도 중...")
            client = BleakClient(ble_address, timeout=15.0)
            await client.connect()
            
            if not client.is_connected:
                print("❌ GATT 연결 실패")
                return None
            
            try:
                # UUID 또는 Handle로 특성 읽기
                # 숫자만 있으면 handle, 아니면 UUID
                if uuid.isdigit():
                    handle = int(uuid)
                    print(f"   Handle {handle}로 읽기 중...")
                    value = await client.read_gatt_char(handle)
                else:
                    print(f"   UUID {uuid}로 읽기 중...")
                    value = await client.read_gatt_char(uuid)
                
                print("✅ 읽기 성공!")
                print(f"   데이터 (bytes): {value}")
                print(f"   데이터 (hex): {value.hex()}")
                print(f"   데이터 (int): {list(value)}")
                
                await client.disconnect()
                return value
                
            except Exception as e:
                print(f"❌ 특성 읽기 실패: {e}")
                await client.disconnect()
                return None
                
        except Exception as e:
            print(f"❌ GATT 연결 실패: {e}")
            return None
    
    async def write_gatt_characteristic(self, address: str, uuid: str, data: bytes, name: str = "Unknown", ble_address: Optional[str] = None, is_connected: bool = False) -> bool:
        """
        특정 UUID의 GATT 특성(Characteristic)에 쓰기
        
        Args:
            address: 장치 주소 (MAC)
            uuid: 쓸 특성의 UUID
            data: 쓸 데이터 (bytes)
            name: 장치 이름
            ble_address: BLE UUID (있으면 이것을 사용)
            is_connected: 시스템에 연결되어 있는지 여부
        
        Returns:
            성공 여부
        """
        try:
            print(f"\n✍️  {name}의 UUID {uuid}에 쓰기 시도...")
            print(f"   데이터 (bytes): {data}")
            print(f"   데이터 (hex): {data.hex()}")
            
            # BLE UUID 필수
            if not ble_address:
                print("❌ BLE UUID가 없어 GATT 연결을 할 수 없습니다.")
                print("   💡 이 장치는 BLE UUID가 없어서 GATT 작업이 불가능합니다.")
                return False
            
            print(f"   BLE 주소: {ble_address}")
            
            # 시스템에 연결되어 있으면 먼저 해제
            if is_connected:
                print("⚠️  장치가 시스템에 연결되어 있습니다.")
                print("   GATT 연결을 위해 시스템 연결을 일시적으로 해제합니다...")
                self.disconnect_device_system(address, name)
                await asyncio.sleep(2)
            
            # GATT 연결
            print("   BleakClient로 연결 시도 중...")
            client = BleakClient(ble_address, timeout=15.0)
            await client.connect()
            
            if not client.is_connected:
                print("❌ GATT 연결 실패")
                return False
            
            try:
                # UUID 또는 Handle로 특성 쓰기
                if uuid.isdigit():
                    handle = int(uuid)
                    print(f"   Handle {handle}로 쓰기 중...")
                    await client.write_gatt_char(handle, data)
                else:
                    print(f"   UUID {uuid}로 쓰기 중...")
                    await client.write_gatt_char(uuid, data)
                
                print("✅ 쓰기 성공!")
                
                await client.disconnect()
                return True
                
            except Exception as e:
                print(f"❌ 특성 쓰기 실패: {e}")
                await client.disconnect()
                return False
                
        except Exception as e:
            print(f"❌ GATT 연결 실패: {e}")
            return False
    
    async def list_all_services_and_characteristics(self, address: str, name: str = "Unknown", ble_address: Optional[str] = None, is_connected: bool = False):
        """
        장치의 모든 서비스와 특성 나열
        (어떤 UUID들이 있는지 탐색)
        """
        try:
            print(f"\n🔍 {name}의 GATT 서비스/특성 탐색 중...")
            
            # BLE UUID 필수
            if not ble_address:
                print("❌ BLE UUID가 없어 GATT 연결을 할 수 없습니다.")
                print("   💡 이 장치는 BLE UUID가 없어서 GATT 작업이 불가능합니다.")
                return
            
            print(f"   BLE 주소: {ble_address}")
            
            # 시스템에 연결되어 있으면 먼저 해제
            if is_connected:
                print("⚠️  장치가 시스템에 연결되어 있습니다.")
                print("   GATT 연결을 위해 시스템 연결을 일시적으로 해제합니다...")
                self.disconnect_device_system(address, name)
                await asyncio.sleep(2)  # 연결 해제 대기
            
            # GATT 연결
            print("   BleakClient로 연결 시도 중...")
            client = BleakClient(ble_address, timeout=15.0)
            await client.connect()
            
            if not client.is_connected:
                print("❌ GATT 연결 실패")
                return
            
            print("\n" + "=" * 80)
            print(f"📋 {name} - GATT 서비스 및 특성")
            print("=" * 80)
            
            services = client.services
            
            for service in services:
                print(f"\n🔧 서비스: {service.uuid}")
                print(f"   설명: {service.description}")
                
                for char in service.characteristics:
                    print(f"\n   📝 특성: {char.uuid}")
                    print(f"      핸들: {char.handle}")
                    print(f"      설명: {char.description}")
                    print(f"      속성: {', '.join(char.properties)}")
                    
                    # 읽기 가능하면 값 읽어보기 (handle 사용)
                    if "read" in char.properties:
                        try:
                            # handle을 사용하여 읽기 (같은 UUID가 여러 개 있을 수 있음)
                            value = await client.read_gatt_char(char.handle)
                            print(f"      현재값 (bytes): {value}")
                            print(f"      현재값 (hex): {value.hex()}")
                            print(f"      현재값 (int): {list(value)}")
                        except Exception as e:
                            # 읽기 실패는 정상 - 일부 특성은 읽기가 거부됨
                            error_msg = str(e)
                            if "Multiple Characteristics" in error_msg:
                                print(f"      현재값: ⚠️ 같은 UUID 중복 (handle {char.handle} 사용 필요)")
                            elif "not supported" in error_msg:
                                print(f"      현재값: ⚠️ 읽기 미지원")
                            else:
                                print(f"      현재값: ⚠️ 읽기 실패")
            
            print("\n" + "=" * 80)
            
            await client.disconnect()
            
        except Exception as e:
            print(f"❌ 서비스 탐색 실패: {e}")

async def main():
    """메인 함수 - 다중 장치 관리"""
    print("=" * 80)
    print("🎧 macOS 하이브리드 Bluetooth 매니저 (다중 장치)")
    print("   (시스템 블루투스 + 범용 미디어 제어 + 배터리 정보)")
    print("=" * 80)
    
    manager = BluetoothHybridManager()
    
    # 연결된 장치들 저장
    connected_devices = {}  # {address: device_info}
    
    while True:
        print("\n" + "=" * 80)
        print("📱 메인 메뉴")
        print("=" * 80)
        print("  1. 장치 검색 및 연결")
        print("  2. 연결된 장치 목록")
        print("  3. 장치 제어 (GATT 읽기/쓰기)")
        print("  4. 미디어 제어")
        print("  0. 종료")
        print("\n선택: ", end="")
        
        try:
            choice = input().strip()
            
            if choice == "1":
                # 장치 검색 및 연결
                devices = await manager.scan_all_devices()
                
                if not devices:
                    print("\n⚠️  장치를 찾을 수 없습니다.")
                    continue
                
                # 장치 목록 출력
                print(f"\n발견된 장치: {len(devices)}개")
                print("=" * 80)
                
                for idx, device in enumerate(devices, 1):
                    already_connected = "✅" if device['address'] in connected_devices else "⚪"
                    status = "연결됨" if device.get('connected') else "연결 안됨"
                    print(f"{idx}. {already_connected} {device['name']}")
                    print(f"   MAC: {device['address']}")
                    
                    # BLE UUID 표시
                    if 'ble_addresses_all' in device:
                        print(f"   BLE: {len(device['ble_addresses_all'])}개 🔵")
                    elif 'ble_address' in device:
                        print(f"   BLE: ✓ 🔵")
                    else:
                        print(f"   BLE: 없음 ⚪")
                    
                    print(f"   시스템: {status}")
                    print("-" * 80)
                
                print("\n연결할 장치 번호 (여러 개는 쉼표로 구분, 0: 취소): ", end="")
                
                selection = input().strip()
                if selection == "0":
                    continue
                
                # 여러 장치 선택 처리
                try:
                    selected_indices = [int(x.strip()) for x in selection.split(",")]
                    
                    for idx in selected_indices:
                        if 1 <= idx <= len(devices):
                            device = devices[idx - 1]
                            
                            # 이미 연결되어 있는지 확인
                            if device['address'] in connected_devices:
                                print(f"\n⚠️  {device['name']}는 이미 연결되어 있습니다.")
                                continue
                            
                            # 연결 시도
                            if not device.get('connected'):
                                success = manager.connect_device_system(device['address'], device['name'])
                                if success:
                                    connected_devices[device['address']] = device
                                    print(f"✅ {device['name']} 연결 완료")
                                await asyncio.sleep(0.5)
                            else:
                                # 이미 시스템에 연결됨
                                connected_devices[device['address']] = device
                                print(f"✅ {device['name']} (이미 시스템에 연결됨)")
                        else:
                            print(f"⚠️  잘못된 번호: {idx}")
                
                except ValueError:
                    print("⚠️  올바른 숫자를 입력하세요.")
            
            elif choice == "2":
                # 연결된 장치 목록
                if not connected_devices:
                    print("\n⚠️  연결된 장치가 없습니다.")
                else:
                    print(f"\n📱 연결된 장치 목록 ({len(connected_devices)}개):")
                    print("=" * 80)
                    for idx, (address, device) in enumerate(connected_devices.items(), 1):
                        print(f"{idx}. {device['name']}")
                        print(f"   MAC: {address}")
                        if 'ble_address' in device:
                            print(f"   BLE: {device['ble_address']} 🔵")
                        print("-" * 80)
            
            elif choice == "3":
                # 장치 제어
                if not connected_devices:
                    print("\n⚠️  연결된 장치가 없습니다.")
                    continue
                
                print(f"\n제어할 장치를 선택하세요:")
                print("=" * 80)
                devices_list = list(connected_devices.items())
                for idx, (address, device) in enumerate(devices_list, 1):
                    print(f"{idx}. {device['name']}")
                print("0. 취소")
                print("\n선택: ", end="")
                
                try:
                    dev_choice = int(input())
                    if dev_choice == 0:
                        continue
                    if 1 <= dev_choice <= len(devices_list):
                        address, selected_device = devices_list[dev_choice - 1]
                        
                        # 장치 제어 메뉴
                        while True:
                            print(f"\n{'='*80}")
                            print(f"🎛️  {selected_device['name']} 제어")
                            print("=" * 80)
                            print("  gatt    - GATT 서비스/특성 탐색 🔍")
                            print("  read    - UUID/Handle로 특성 읽기 📖")
                            print("  write   - UUID/Handle로 특성 쓰기 ✍️")
                            print("  disc    - 연결 해제")
                            print("  back    - 뒤로")
                            print("\n명령: ", end="")
                            
                            cmd = input().strip().lower()
                            
                            if cmd == "gatt":
                                await manager.list_all_services_and_characteristics(
                                    selected_device['address'],
                                    selected_device['name'],
                                    selected_device.get('ble_address'),
                                    selected_device.get('connected', False)
                                )
                            
                            elif cmd == "read":
                                print("\n읽을 특성의 UUID 또는 Handle: ", end="")
                                identifier = input().strip()
                                if identifier:
                                    await manager.read_gatt_characteristic(
                                        selected_device['address'],
                                        identifier,
                                        selected_device['name'],
                                        selected_device.get('ble_address'),
                                        selected_device.get('connected', False)
                                    )
                            
                            elif cmd == "write":
                                print("\n쓸 특성의 UUID 또는 Handle: ", end="")
                                uuid = input().strip()
                                if not uuid:
                                    continue
                                
                                print("데이터 (1,2,3,4 또는 0x01020304 또는 Hello): ", end="")
                                data_input = input().strip()
                                if not data_input:
                                    continue
                                
                                try:
                                    if data_input.startswith('0x'):
                                        data = bytes.fromhex(data_input[2:])
                                    elif ',' in data_input:
                                        data = bytes([int(x.strip()) for x in data_input.split(',')])
                                    else:
                                        data = data_input.encode('utf-8')
                                    
                                    await manager.write_gatt_characteristic(
                                        selected_device['address'],
                                        uuid,
                                        data,
                                        selected_device['name'],
                                        selected_device.get('ble_address'),
                                        selected_device.get('connected', False)
                                    )
                                except Exception as e:
                                    print(f"❌ 데이터 형식 오류: {e}")
                            
                            elif cmd == "disc":
                                manager.disconnect_device_system(address, selected_device['name'])
                                del connected_devices[address]
                                print(f"✅ {selected_device['name']} 연결 해제 완료")
                                break
                            
                            elif cmd == "back":
                                break
                            
                            else:
                                print(f"알 수 없는 명령: {cmd}")
                    
                except ValueError:
                    print("올바른 숫자를 입력하세요.")
            
            elif choice == "4":
                # 미디어 제어
                print("\n🎵 범용 미디어 제어")
                print("=" * 80)
                print("  play  - 재생/일시정지 ▶️⏸️")
                print("  next  - 다음 트랙 ⏭️")
                print("  prev  - 이전 트랙 ⏮️")
                print("  info  - 현재 재생 정보 📋")
                print("  audio - 오디오 출력 장치 변경")
                print("  back  - 뒤로")
                
                while True:
                    print("\n> ", end="")
                    cmd = input().strip().lower()
                    
                    if cmd == "play":
                        manager.media_play_pause()
                    elif cmd == "next":
                        manager.media_next()
                    elif cmd == "prev":
                        manager.media_previous()
                    elif cmd == "info":
                        manager.media_info()
                    elif cmd == "audio":
                        audio_devices = manager.get_audio_devices()
                        print("\n사용 가능한 오디오 출력 장치:")
                        for i, dev in enumerate(audio_devices, 1):
                            print(f"{i}. {dev}")
                        print("\n선택 (0: 취소): ", end="")
                        try:
                            audio_choice = int(input())
                            if 1 <= audio_choice <= len(audio_devices):
                                manager.switch_audio_output(audio_devices[audio_choice - 1])
                        except (ValueError, IndexError):
                            print("취소")
                    elif cmd == "back":
                        break
                    else:
                        print(f"알 수 없는 명령: {cmd}")
            
            elif choice == "0":
                print("\n종료합니다...")
                # 모든 장치 연결 해제
                for address, device in list(connected_devices.items()):
                    manager.disconnect_device_system(address, device['name'])
                break
            
            else:
                print("잘못된 선택입니다.")
        
        except KeyboardInterrupt:
            print("\n\n종료합니다...")
            break
        except Exception as e:
            print(f"오류 발생: {e}")


if __name__ == "__main__":
    asyncio.run(main())
