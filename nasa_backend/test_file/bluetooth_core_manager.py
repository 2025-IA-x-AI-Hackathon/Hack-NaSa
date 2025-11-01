"""
Hybrid Bluetooth 기기 제어

- 연결: blueutil (macOS 시스템 Bluetooth - 안정적)
- 정보 읽기: BLE GATT (배터리 등)
- 오디오 제어: 직접 GATT 특성 제어
"""

import asyncio
import subprocess
from typing import List, Dict, Optional
from bleak import BleakScanner, BleakClient

# PyObjC 임포트
try:
    from Foundation import NSObject, NSRunLoop, NSDefaultRunLoopMode, NSDate
    from CoreBluetooth import (
        CBCentralManager,
        CBPeripheral,
        CBUUID,
        CBCentralManagerStatePoweredOn,
        CBCharacteristicWriteWithResponse,
        CBCharacteristicWriteWithoutResponse
    )
    from IOBluetooth import (
        IOBluetoothDevice,
        IOBluetoothDeviceInquiry
    )
    PYOBJC_AVAILABLE = True
except ImportError:
    PYOBJC_AVAILABLE = False
    print("⚠️  PyObjC를 사용할 수 없습니다. BLE 기능만 제공됩니다.")


class BluetoothCoreManager:
    """Hybrid Bluetooth 관리 - 시스템 연결 + GATT 제어"""
    
    def __init__(self):
        self.connected_devices: Dict[str, BleakClient] = {}  # BLE GATT 클라이언트
        self.system_connected: Dict[str, str] = {}  # 시스템 연결된 장치 {address: name}
        self.check_blueutil()
    
    def check_blueutil(self):
        """blueutil 설치 확인"""
        result = subprocess.run(
            ["which", "blueutil"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("⚠️  blueutil이 설치되지 않았습니다.")
            print("설치: brew install blueutil")
    
    # ========================================================================
    # 시스템 Bluetooth 연결 (blueutil)
    # ========================================================================
    
    def get_paired_devices(self) -> List[Dict[str, str]]:
        """blueutil로 페어링된 장치 목록 조회"""
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
    
    def connect_device(self, address: str, name: str = "Unknown") -> bool:
        """
        blueutil로 시스템 Bluetooth 연결
        (Classic + A2DP 자동 연결)
        """
        try:
            print(f"\n📱 '{name}' 연결 중...")
            
            result = subprocess.run(
                ["blueutil", "--connect", address],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                self.system_connected[address] = name
                print(f"✅ '{name}' 시스템 연결 성공!")
                
                # 연결 안정화 대기
                import time
                time.sleep(2)
                return True
            else:
                print(f"❌ 연결 실패: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 연결 중 오류: {e}")
            return False
    
    def disconnect_device(self, address: str) -> bool:
        """시스템 Bluetooth 연결 해제"""
        try:
            name = self.system_connected.get(address, "Unknown")
            print(f"\n🔌 '{name}' 연결 해제 중...")
            
            result = subprocess.run(
                ["blueutil", "--disconnect", address],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                if address in self.system_connected:
                    del self.system_connected[address]
                print(f"✅ '{name}' 연결 해제 완료")
                return True
            else:
                print(f"❌ 연결 해제 실패")
                return False
                
        except Exception as e:
            print(f"❌ 연결 해제 중 오류: {e}")
            return False
    
    # ========================================================================
    # 기기 탐색 (BLE - bleak 사용)
    # ========================================================================
    
    async def scan_ble_devices(self, timeout: float = 5.0) -> List[Dict[str, str]]:
        """
        BLE 장치 스캔
        
        Returns:
            장치 목록 [{"address": "...", "name": "...", "rssi": -50}]
        """
        print(f"🔍 BLE 장치 스캔 중 ({timeout}초)...")
        
        devices = []
        async with BleakScanner() as scanner:
            await asyncio.sleep(timeout)
            discovered = scanner.discovered_devices_and_advertisement_data
            
            for address, (device, adv_data) in discovered.items():
                if adv_data.rssi > -80:  # 신호가 있는 장치만
                    name = device.name or "Unknown"
                    devices.append({
                        "address": address,
                        "name": name,
                        "rssi": adv_data.rssi,
                        "type": "BLE"
                    })
        
        print(f"✅ {len(devices)}개 BLE 장치 발견")
        return devices
    
    # ========================================================================
    # BLE GATT 연결 (정보 읽기용 - 필요시에만)
    # ========================================================================
    
    async def _ensure_gatt_connection(self, address: str) -> Optional[BleakClient]:
        """
        GATT 연결 확보 (없으면 생성, 있으면 재사용)
        내부 헬퍼 함수
        """
        # 이미 GATT 연결되어 있으면 재사용
        if address in self.connected_devices:
            if self.connected_devices[address].is_connected:
                return self.connected_devices[address]
            else:
                # 연결 끊긴 경우 제거
                del self.connected_devices[address]
        
        # 새 GATT 연결 시도
        try:
            print(f"🔗 GATT 연결 시도 중...")
            client = BleakClient(address, timeout=10.0)
            await client.connect()
            
            if client.is_connected:
                self.connected_devices[address] = client
                services = list(client.services)
                print(f"✅ GATT 연결 성공 ({len(services)}개 서비스)")
                return client
            else:
                print(f"❌ GATT 연결 실패")
                return None
                
        except Exception as e:
            print(f"❌ GATT 연결 오류: {e}")
            return None
    
    # ========================================================================
    # 배터리 정보 (표준 Battery Service)
    # ========================================================================
    
    async def get_battery_level(self, address: str) -> Optional[int]:
        """
        장치의 배터리 레벨 조회
        
        표준 Battery Service (0x180F) 사용
        Battery Level Characteristic (0x2A19)
        
        Args:
            address: 장치 주소
        
        Returns:
            배터리 퍼센트 (0-100) 또는 None
        """
        # GATT 연결 확보 (없으면 자동 생성)
        client = await self._ensure_gatt_connection(address)
        if not client:
            print(f"⚠️  GATT 연결 실패")
            return None
        
        try:
            # 표준 Battery Service UUID
            BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
            BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
            
            print(f"🔋 배터리 정보 조회 중...")
            
            # 모든 서비스 탐색
            for service in client.services:
                # Battery Service 찾기
                if BATTERY_SERVICE_UUID.lower() in service.uuid.lower():
                    print(f"✅ Battery Service 발견: {service.uuid}")
                    
                    # Battery Level Characteristic 찾기
                    for char in service.characteristics:
                        if BATTERY_LEVEL_UUID.lower() in char.uuid.lower():
                            # 배터리 레벨 읽기
                            value = await client.read_gatt_char(char.handle)
                            battery_level = int(value[0])
                            
                            # 배터리 상태 이모지
                            if battery_level >= 90:
                                emoji = "🔋"
                            elif battery_level >= 60:
                                emoji = "🔋"
                            elif battery_level >= 30:
                                emoji = "🪫"
                            else:
                                emoji = "🪫"
                            
                            print(f"{emoji} 배터리: {battery_level}%")
                            return battery_level
            
            # Battery Service를 찾지 못한 경우 전체 서비스 출력
            print(f"⚠️  Battery Service를 찾을 수 없습니다.")
            print(f"사용 가능한 서비스:")
            for service in client.services:
                print(f"  - {service.uuid}: {service.description}")
            
            return None
            
        except Exception as e:
            print(f"❌ 배터리 조회 실패: {e}")
            return None
    
    async def get_detailed_battery_info(self, address: str) -> Optional[Dict]:
        """
        상세 배터리 정보 조회 (좌/우 이어버드, 케이스 등)
        
        Galaxy Buds 같은 기기에서 사용
        """
        client = await self._ensure_gatt_connection(address)
        if not client:
            return None
        battery_info = {}
        
        try:
            # 다양한 배터리 관련 특성 탐색
            for service in client.services:
                for char in service.characteristics:
                    char_uuid = char.uuid.lower()
                    
                    # 배터리 관련 특성 감지
                    if "battery" in char.description.lower() or "2a19" in char_uuid:
                        if "read" in char.properties:
                            try:
                                value = await client.read_gatt_char(char.handle)
                                
                                # 특성 이름에서 위치 파악
                                desc = char.description.lower()
                                if "left" in desc:
                                    battery_info["left"] = int(value[0])
                                elif "right" in desc:
                                    battery_info["right"] = int(value[0])
                                elif "case" in desc:
                                    battery_info["case"] = int(value[0])
                                else:
                                    battery_info["main"] = int(value[0])
                                    
                            except Exception as e:
                                continue
            
            if battery_info:
                print(f"🔋 상세 배터리 정보:")
                for key, value in battery_info.items():
                    print(f"  {key.capitalize()}: {value}%")
                return battery_info
            
            return None
            
        except Exception as e:
            print(f"❌ 상세 배터리 조회 실패: {e}")
            return None
    
    # ========================================================================
    # 블루투스 스피커/오디오 제어
    # ========================================================================
    
    async def audio_set_volume(self, address: str, volume: int) -> bool:
        """
        오디오 볼륨 설정
        
        Args:
            address: 장치 주소
            volume: 볼륨 레벨 (0-100)
        
        Returns:
            성공 여부
        """
        client = await self._ensure_gatt_connection(address)
        if not client:
            return False
        
        try:
            # Volume Control Service UUID (표준)
            VOLUME_SERVICE_UUID = "00001844-0000-1000-8000-00805f9b34fb"
            VOLUME_STATE_UUID = "00002b7d-0000-1000-8000-00805f9b34fb"
            VOLUME_CONTROL_UUID = "00002b7e-0000-1000-8000-00805f9b34fb"
            
            # 볼륨 값 범위 체크
            if not 0 <= volume <= 100:
                print(f"⚠️  볼륨은 0-100 사이여야 합니다.")
                return False
            
            print(f"🔊 볼륨 설정 중: {volume}%")
            
            # 모든 서비스에서 볼륨 관련 특성 찾기
            for service in client.services:
                for char in service.characteristics:
                    char_uuid = char.uuid.lower()
                    
                    # 볼륨 제어 특성 감지
                    if ("volume" in char.description.lower() or 
                        "2b7e" in char_uuid or "2b7d" in char_uuid):
                        
                        if "write" in char.properties or "write-without-response" in char.properties:
                            try:
                                # 볼륨 값 전송 (0-255 범위로 변환)
                                volume_byte = int((volume / 100) * 255)
                                await client.write_gatt_char(
                                    char.handle,
                                    bytes([volume_byte]),
                                    response=False
                                )
                                print(f"✅ 볼륨 설정 완료: {volume}%")
                                return True
                                
                            except Exception as e:
                                print(f"   시도 실패: {e}")
                                continue
            
            print(f"⚠️  볼륨 제어 특성을 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            print(f"❌ 볼륨 설정 실패: {e}")
            return False
    
    async def audio_mute(self, address: str, mute: bool = True) -> bool:
        """
        오디오 음소거
        
        Args:
            address: 장치 주소
            mute: True=음소거, False=해제
        
        Returns:
            성공 여부
        """
        client = await self._ensure_gatt_connection(address)
        if not client:
            return False
        
        try:
            VOLUME_SERVICE_UUID = "00001844-0000-1000-8000-00805f9b34fb"
            MUTE_UUID = "00002bc3-0000-1000-8000-00805f9b34fb"
            
            status = "음소거" if mute else "음소거 해제"
            print(f"🔇 오디오 {status} 중...")
            
            for service in client.services:
                for char in service.characteristics:
                    char_uuid = char.uuid.lower()
                    
                    if "mute" in char.description.lower() or "2bc3" in char_uuid:
                        if "write" in char.properties or "write-without-response" in char.properties:
                            try:
                                mute_value = bytes([0x01 if mute else 0x00])
                                await client.write_gatt_char(
                                    char.handle,
                                    mute_value,
                                    response=False
                                )
                                print(f"✅ {status} 완료")
                                return True
                                
                            except Exception as e:
                                print(f"   시도 실패: {e}")
                                continue
            
            print(f"⚠️  음소거 제어 특성을 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            print(f"❌ 음소거 설정 실패: {e}")
            return False
    
    async def audio_get_volume(self, address: str) -> Optional[int]:
        """
        현재 볼륨 레벨 조회
        
        Returns:
            볼륨 레벨 (0-100) 또는 None
        """
        client = await self._ensure_gatt_connection(address)
        if not client:
            return None
        
        try:
            for service in client.services:
                for char in service.characteristics:
                    if "volume" in char.description.lower():
                        if "read" in char.properties:
                            try:
                                value = await client.read_gatt_char(char.handle)
                                # 0-255 범위를 0-100으로 변환
                                volume = int((value[0] / 255) * 100)
                                print(f"🔊 현재 볼륨: {volume}%")
                                return volume
                            except:
                                continue
            
            return None
            
        except Exception as e:
            print(f"❌ 볼륨 조회 실패: {e}")
            return None
    
    async def audio_set_equalizer(self, address: str, preset: str) -> bool:
        """
        이퀄라이저 프리셋 설정
        
        Args:
            address: 장치 주소
            preset: "normal", "bass_boost", "treble_boost", "vocal", "custom"
        
        Returns:
            성공 여부
        """
        client = await self._ensure_gatt_connection(address)
        if not client:
            return False
        
        try:
            # EQ 프리셋 매핑
            eq_presets = {
                "normal": 0x00,
                "bass_boost": 0x01,
                "treble_boost": 0x02,
                "vocal": 0x03,
                "custom": 0x04
            }
            
            if preset not in eq_presets:
                print(f"⚠️  지원하지 않는 프리셋: {preset}")
                return False
            
            print(f"🎵 이퀄라이저 설정: {preset}")
            
            for service in client.services:
                for char in service.characteristics:
                    desc = char.description.lower()
                    
                    if "equalizer" in desc or "eq" in desc or "audio" in desc:
                        if "write" in char.properties or "write-without-response" in char.properties:
                            try:
                                eq_value = bytes([eq_presets[preset]])
                                await client.write_gatt_char(
                                    char.handle,
                                    eq_value,
                                    response=False
                                )
                                print(f"✅ 이퀄라이저 설정 완료")
                                return True
                            except Exception as e:
                                continue
            
            print(f"⚠️  이퀄라이저 제어 특성을 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            print(f"❌ 이퀄라이저 설정 실패: {e}")
            return False
    
    # ========================================================================
    # 장치 정보 조회
    # ========================================================================
    
    async def get_device_services(self, address: str) -> List[Dict]:
        """
        장치의 모든 서비스 목록 조회
        
        Returns:
            [{"uuid": "...", "description": "...", "characteristics": [...]}]
        """
        client = await self._ensure_gatt_connection(address)
        if not client:
            return []
        services_info = []
        
        try:
            print(f"\n📋 장치 서비스 정보:")
            print("=" * 80)
            
            for service in client.services:
                chars_info = []
                
                for char in service.characteristics:
                    char_data = {
                        "uuid": char.uuid,
                        "handle": char.handle,
                        "properties": char.properties,
                        "description": char.description
                    }
                    chars_info.append(char_data)
                
                service_data = {
                    "uuid": service.uuid,
                    "description": service.description,
                    "characteristics": chars_info
                }
                services_info.append(service_data)
                
                print(f"\n🔧 서비스: {service.uuid}")
                print(f"   설명: {service.description}")
                print(f"   특성: {len(chars_info)}개")
            
            print("=" * 80)
            return services_info
            
        except Exception as e:
            print(f"❌ 서비스 정보 조회 실패: {e}")
            return []


# ============================================================================
# 테스트 코드
# ============================================================================

async def main():
    """테스트 메인 함수"""
    print("=" * 80)
    print("🎧 Hybrid Bluetooth 장치 제어")
    print("   (시스템 연결 + GATT 정보)")
    print("=" * 80)
    
    manager = BluetoothCoreManager()
    
    # 1. 페어링된 장치 조회
    devices = manager.get_paired_devices()
    
    if not devices:
        print("\n⚠️  페어링된 장치가 없습니다.")
        print("시스템 설정에서 장치를 먼저 페어링해주세요.")
        return
    
    # 2. 장치 목록 출력
    print(f"\n페어링된 장치: {len(devices)}개")
    print("=" * 80)
    for idx, device in enumerate(devices, 1):
        status = "✅ 연결됨" if device['connected'] else "⚪ 연결 안됨"
        print(f"{idx}. {device['name']}")
        print(f"   주소: {device['address']}")
        print(f"   상태: {status}")
        print("-" * 80)
    
    # 3. 연결할 장치 선택
    print("\n연결할 장치 번호 (0: 취소): ", end="")
    try:
        choice = int(input())
        if choice < 1 or choice > len(devices):
            print("취소")
            return
        
        selected = devices[choice - 1]
        address = selected["address"]
        name = selected["name"]
        
        # 4. 시스템 연결 (이미 연결된 경우 스킵)
        if not selected['connected']:
            success = manager.connect_device(address, name)
            if not success:
                print("\n⚠️  시스템 연결 실패")
                return
        else:
            print(f"\n✅ '{name}'는 이미 연결되어 있습니다.")
            manager.system_connected[address] = name
        
        # 5. 서비스 정보 조회 (GATT 자동 연결)
        print(f"\n📋 '{name}' 서비스 탐색 중...")
        await manager.get_device_services(address)
        
        # 6. 배터리 정보 (GATT)
        battery = await manager.get_battery_level(address)
        
        # 7. 상세 배터리 정보
        detailed = await manager.get_detailed_battery_info(address)
        
        # 8. 제어 루프
        print("\n" + "=" * 80)
        print(f"🎛️  '{name}' 제어")
        print("=" * 80)
        print("\n명령어:")
        print("  vol <0-100> - 볼륨 설정")
        print("  mute - 음소거")
        print("  unmute - 음소거 해제")
        print("  eq <preset> - 이퀄라이저 (normal/bass_boost/treble_boost)")
        print("  battery - 배터리 확인")
        print("  services - 서비스 재조회")
        print("  disc - 연결 해제")
        print("  q - 종료")
        
        while True:
            cmd = input("\n> ").strip().split()
            
            if not cmd:
                continue
            
            if cmd[0] == "q":
                break
            elif cmd[0] == "vol" and len(cmd) == 2:
                await manager.audio_set_volume(address, int(cmd[1]))
            elif cmd[0] == "mute":
                await manager.audio_mute(address, True)
            elif cmd[0] == "unmute":
                await manager.audio_mute(address, False)
            elif cmd[0] == "eq" and len(cmd) == 2:
                await manager.audio_set_equalizer(address, cmd[1])
            elif cmd[0] == "battery":
                await manager.get_battery_level(address)
                await manager.get_detailed_battery_info(address)
            elif cmd[0] == "services":
                await manager.get_device_services(address)
            elif cmd[0] == "disc":
                manager.disconnect_device(address)
                break
            else:
                print("알 수 없는 명령")
        
        # GATT 연결 정리
        if address in manager.connected_devices:
            await manager.connected_devices[address].disconnect()
            del manager.connected_devices[address]
            print("🔌 GATT 연결 해제")
    
    except ValueError:
        print("올바른 숫자를 입력하세요")
    except KeyboardInterrupt:
        print("\n종료합니다")


if __name__ == "__main__":
    asyncio.run(main())

