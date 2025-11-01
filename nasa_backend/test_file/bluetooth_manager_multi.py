import asyncio
from bleak import BleakScanner, BleakClient
from typing import Optional, List, Dict
import sys
import subprocess
import re
import json
import os


class MultiDeviceBluetoothManager:
    """여러 Bluetooth 장치를 동시에 관리하는 클래스"""
    
    def __init__(self):
        self.connected_clients: Dict[str, BleakClient] = {}  # {address: BleakClient}
        self.device_names: Dict[str, str] = {}  # {address: name}
        self.known_devices_file = "known_bluetooth_devices.json"
        self.known_devices: Dict[str, str] = self.load_known_devices()  # {address: name}
    
    def load_known_devices(self) -> Dict[str, str]:
        """저장된 알려진 장치 목록을 로드합니다."""
        if os.path.exists(self.known_devices_file):
            try:
                with open(self.known_devices_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  장치 목록 로드 실패: {e}")
                return {}
        return {}
    
    def save_known_devices(self):
        """알려진 장치 목록을 저장합니다."""
        try:
            with open(self.known_devices_file, 'w') as f:
                json.dump(self.known_devices, f, indent=2)
        except Exception as e:
            print(f"⚠️  장치 목록 저장 실패: {e}")
    
    def add_known_device(self, address: str, name: str):
        """장치를 알려진 장치 목록에 추가합니다."""
        self.known_devices[address] = name
        self.save_known_devices()
    
    async def quick_scan_nearby_devices(self, timeout: float = 2.0) -> List[dict]:
        """
        주변의 강한 신호 장치만 빠르게 스캔합니다.
        
        Args:
            timeout: 스캔 시간 (초)
        
        Returns:
            스캔된 장치 목록
        """
        print(f"🔍 근처 장치를 빠르게 스캔합니다 ({timeout}초)...")
        
        device_list = []
        
        async with BleakScanner() as scanner:
            await asyncio.sleep(timeout)
            devices = scanner.discovered_devices_and_advertisement_data
            
            for address, (device, adv_data) in devices.items():
                # 신호가 강한 장치만 (근처에 있는 장치)
                if adv_data.rssi > -65:
                    device_name = device.name
                    if not device_name and hasattr(adv_data, 'local_name'):
                        device_name = adv_data.local_name
                    if not device_name:
                        device_name = "Unknown"
                    
                    device_list.append({
                        "name": device_name,
                        "address": address,
                        "rssi": adv_data.rssi
                    })
        
        return device_list
    
    async def load_and_connect_known_devices(self) -> int:
        """
        저장된 알려진 장치들에 자동으로 재연결을 시도합니다.
        스캔 없이 저장된 주소로 바로 연결합니다.
        
        Returns:
            연결 성공한 장치 수
        """
        if not self.known_devices:
            print("⚠️  저장된 장치가 없습니다. 처음 사용 시 장치를 추가해주세요.")
            return 0
        
        print(f"\n📱 저장된 {len(self.known_devices)}개 장치에 재연결을 시도합니다...")
        print("-" * 80)
        
        success_count = 0
        
        for address, name in self.known_devices.items():
            print(f"\n연결 시도: {name}")
            result = await self.connect_device(address, name)
            if result:
                success_count += 1
            await asyncio.sleep(0.3)  # 연결 간 짧은 대기
        
        print("\n" + "=" * 80)
        print(f"✅ 재연결 완료: {success_count}/{len(self.known_devices)}개 장치")
        print("=" * 80)
        
        return success_count
    
    async def discover_and_add_devices(self, timeout: float = 5.0):
        """
        새로운 장치를 검색하고 알려진 장치 목록에 추가합니다.
        """
        print(f"\n🔍 새로운 장치를 검색합니다 ({timeout}초)...")
        
        devices = await self.quick_scan_nearby_devices(timeout)
        
        if not devices:
            print("⚠️  근처에서 장치를 찾을 수 없습니다.")
            return
        
        print(f"\n발견된 장치: {len(devices)}개")
        print("=" * 80)
        
        for idx, device in enumerate(devices, 1):
            already_known = "✅" if device["address"] in self.known_devices else "🆕"
            print(f"{idx}. {already_known} {device['name']}")
            print(f"   주소: {device['address']}")
            print(f"   신호: {device['rssi']} dBm")
            print("-" * 80)
        
        print("\n추가할 장치 번호를 입력하세요 (여러 개는 쉼표로 구분, 0: 취소): ", end="")
        choice = input().strip()
        
        if choice == "0":
            print("취소되었습니다.")
            return
        
        # 여러 장치 선택 처리
        try:
            selected_indices = [int(x.strip()) for x in choice.split(",")]
            
            for idx in selected_indices:
                if 1 <= idx <= len(devices):
                    device = devices[idx - 1]
                    
                    # 바로 연결 시도 (연결 성공 시 자동으로 저장됨)
                    await self.connect_device(device["address"], device["name"])
                    await asyncio.sleep(0.3)
                else:
                    print(f"⚠️  잘못된 번호: {idx}")
        
        except ValueError:
            print("⚠️  올바른 숫자를 입력하세요.")
    
    async def scan_devices(self, timeout: float = 5.0) -> List[dict]:
        """
        주변 Bluetooth 장치를 스캔합니다.
        
        Args:
            timeout: 스캔 시간 (초)
        
        Returns:
            스캔된 장치 목록
        """
        print(f"🔍 {timeout}초 동안 Bluetooth 장치를 스캔합니다...")
        
        device_list = []
        
        # BleakScanner를 사용하여 장치와 광고 데이터를 함께 수집
        async with BleakScanner() as scanner:
            await asyncio.sleep(timeout)
            devices = scanner.discovered_devices_and_advertisement_data
            
            print(f"\n발견된 장치: {len(devices)}개")
            print("-" * 80)
            
            for idx, (address, (device, adv_data)) in enumerate(devices.items(), 1):
                # 장치 이름 우선순위: device.name > local_name > Unknown
                device_name = device.name
                if not device_name and hasattr(adv_data, 'local_name'):
                    device_name = adv_data.local_name
                if not device_name:
                    device_name = "Unknown"
                
                device_info = {
                    "index": idx,
                    "name": device_name,
                    "address": address,
                    "rssi": adv_data.rssi
                }
                device_list.append(device_info)
                print(f"{idx}. 이름: {device_info['name']}")
                print(f"   주소: {device_info['address']}")
                print(f"   신호강도(RSSI): {device_info['rssi']} dBm")
                print("-" * 80)
        
        return device_list
    
    async def connect_device(self, address: str, name: str = "Unknown") -> bool:
        """
        특정 주소의 Bluetooth 장치에 연결합니다.
        
        Args:
            address: 연결할 장치의 MAC 주소
            name: 장치 이름
        
        Returns:
            연결 성공 여부
        """
        # 이미 연결되어 있는지 확인
        if address in self.connected_clients:
            if self.connected_clients[address].is_connected:
                print(f"⚠️  이미 연결된 장치입니다: {name}")
                return True
            else:
                # 연결이 끊긴 경우 제거
                del self.connected_clients[address]
                del self.device_names[address]
        
        try:
            print(f"\n📱 장치에 연결 중: {name} ({address})")
            client = BleakClient(address)
            await client.connect()
            
            if client.is_connected:
                self.connected_clients[address] = client
                self.device_names[address] = name
                
                # 연결 성공 시 알려진 장치 목록에 자동 추가
                if address not in self.known_devices:
                    self.add_known_device(address, name)
                    print(f"💾 장치가 자동으로 저장되었습니다.")
                
                print(f"✅ 연결 성공! (연결된 장치: {len(self.connected_clients)}개)")
                return True
            else:
                print("❌ 연결 실패")
                return False
                
        except Exception as e:
            print(f"❌ 연결 중 오류 발생: {e}")
            return False
    
    async def disconnect_device(self, address: str):
        """특정 장치와의 연결을 끊습니다."""
        if address not in self.connected_clients:
            print("⚠️  해당 주소의 연결된 장치가 없습니다.")
            return
        
        client = self.connected_clients[address]
        name = self.device_names.get(address, "Unknown")
        
        if client.is_connected:
            await client.disconnect()
            print(f"🔌 장치 연결 해제됨: {name} ({address})")
        
        del self.connected_clients[address]
        del self.device_names[address]
    
    async def disconnect_all(self):
        """모든 연결된 장치의 연결을 끊습니다."""
        addresses = list(self.connected_clients.keys())
        for address in addresses:
            await self.disconnect_device(address)
        print("✅ 모든 장치 연결 해제 완료")
    
    def list_connected_devices(self):
        """연결된 모든 장치를 출력합니다."""
        if not self.connected_clients:
            print("⚠️  연결된 장치가 없습니다.")
            return
        
        print(f"\n📱 연결된 장치 목록 ({len(self.connected_clients)}개):")
        print("=" * 80)
        for idx, (address, client) in enumerate(self.connected_clients.items(), 1):
            name = self.device_names.get(address, "Unknown")
            status = "✅ 연결됨" if client.is_connected else "❌ 연결 끊김"
            print(f"{idx}. {name}")
            print(f"   주소: {address}")
            print(f"   상태: {status}")
            print("-" * 80)
    
    def get_device_by_index(self, index: int) -> Optional[tuple]:
        """
        인덱스로 장치를 가져옵니다.
        
        Returns:
            (address, client, name) 튜플 또는 None
        """
        if index < 1 or index > len(self.connected_clients):
            return None
        
        addresses = list(self.connected_clients.keys())
        address = addresses[index - 1]
        return (address, self.connected_clients[address], self.device_names[address])
    
    async def toggle_mute(self) -> bool:
        """
        시스템 음소거를 토글합니다 (macOS).
        
        Returns:
            명령 실행 성공 여부
        """
        try:
            # macOS의 현재 음소거 상태 확인
            result = subprocess.run(
                ["osascript", "-e", "output muted of (get volume settings)"],
                capture_output=True,
                text=True
            )
            
            is_muted = result.stdout.strip() == "true"
            
            if is_muted:
                # 음소거 해제
                subprocess.run(
                    ["osascript", "-e", "set volume without output muted"],
                    check=True
                )
                print("🔊 음소거 해제되었습니다!")
            else:
                # 음소거 설정
                subprocess.run(
                    ["osascript", "-e", "set volume with output muted"],
                    check=True
                )
                print("🔇 음소거되었습니다!")
            
            return True
            
        except Exception as e:
            print(f"❌ 음소거 토글 실패: {e}")
            return False
    
    async def get_battery_level(self, address: str) -> Optional[int]:
        """
        특정 Bluetooth 장치의 배터리 레벨을 가져옵니다.
        
        Args:
            address: 장치 주소
        
        Returns:
            배터리 퍼센트 (0-100) 또는 None
        """
        if address not in self.connected_clients:
            print("⚠️  해당 주소의 연결된 장치가 없습니다.")
            return None
        
        client = self.connected_clients[address]
        name = self.device_names.get(address, "Unknown")
        
        if not client.is_connected:
            print(f"⚠️  {name} 장치가 연결되어 있지 않습니다.")
            return None
        
        try:
            # 표준 Battery Service UUID
            BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
            BATTERY_LEVEL_CHAR_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
            
            print(f"🔋 {name} 배터리 정보를 요청합니다...")
            
            # 배터리 서비스 찾기
            services = client.services
            battery_service = None
            
            for service in services:
                if BATTERY_SERVICE_UUID.lower() in service.uuid.lower():
                    battery_service = service
                    break
            
            if not battery_service:
                print(f"⚠️  {name}에서 배터리 서비스를 찾을 수 없습니다.")
                # 모든 서비스에서 배터리 레벨 특성 찾기 시도
                for service in services:
                    for char in service.characteristics:
                        if BATTERY_LEVEL_CHAR_UUID.lower() in char.uuid.lower():
                            try:
                                value = await client.read_gatt_char(char.handle)
                                battery_level = int(value[0])
                                print(f"🔋 {name} 배터리: {battery_level}%")
                                return battery_level
                            except Exception as e:
                                print(f"배터리 정보 읽기 실패: {e}")
                return None
            
            # 배터리 레벨 특성 찾기
            for char in battery_service.characteristics:
                if BATTERY_LEVEL_CHAR_UUID.lower() in char.uuid.lower():
                    try:
                        value = await client.read_gatt_char(char.handle)
                        battery_level = int(value[0])
                        
                        # 배터리 레벨에 따른 이모지 선택
                        if battery_level >= 80:
                            emoji = "🔋"
                        elif battery_level >= 50:
                            emoji = "🔋"
                        elif battery_level >= 20:
                            emoji = "🪫"
                        else:
                            emoji = "🪫"
                        
                        print(f"{emoji} {name} 배터리: {battery_level}%")
                        return battery_level
                    except Exception as e:
                        print(f"❌ 배터리 정보 읽기 실패: {e}")
                        return None
            
            print(f"⚠️  {name}에서 배터리 레벨 특성을 찾을 수 없습니다.")
            return None
            
        except Exception as e:
            print(f"❌ 배터리 정보 조회 실패: {e}")
            return None
    
    async def get_all_battery_levels(self):
        """연결된 모든 장치의 배터리 레벨을 가져옵니다."""
        if not self.connected_clients:
            print("⚠️  연결된 장치가 없습니다.")
            return
        
        print("\n🔋 모든 장치의 배터리 정보:")
        print("=" * 80)
        
        for address in self.connected_clients.keys():
            await self.get_battery_level(address)
        
        print("=" * 80)
    
    async def print_device_info(self, address: str):
        """연결된 장치의 서비스와 특성 정보를 출력합니다."""
        if address not in self.connected_clients:
            print("⚠️  해당 주소의 연결된 장치가 없습니다.")
            return
        
        client = self.connected_clients[address]
        name = self.device_names.get(address, "Unknown")
        
        if not client.is_connected:
            print(f"⚠️  {name} 장치가 연결되어 있지 않습니다.")
            return
        
        print(f"\n📋 {name} 장치 서비스 및 특성 정보:")
        print("=" * 80)
        
        services = client.services
        for service in services:
            print(f"\n🔧 서비스: {service.uuid}")
            print(f"   설명: {service.description}")
            
            for char in service.characteristics:
                print(f"\n   📝 특성: {char.uuid}")
                print(f"      핸들: {char.handle}")
                print(f"      속성: {', '.join(char.properties)}")
                
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.handle)
                        print(f"      값: {value}")
                    except Exception as e:
                        print(f"      값 읽기 실패: {e}")
        
        print("=" * 80)


async def main():
    """테스트용 메인 함수"""
    manager = MultiDeviceBluetoothManager()
    
    print("=" * 80)
    print("🎧 멀티 디바이스 Bluetooth 매니저")
    print("=" * 80)
    
    # 프로그램 시작 시 저장된 장치 자동 로드 및 연결
    if manager.known_devices:
        print(f"\n💾 저장된 장치: {len(manager.known_devices)}개")
        for address, name in manager.known_devices.items():
            print(f"  - {name}")
        
        await manager.load_and_connect_known_devices()
        
        if manager.connected_clients:
            print("\n현재 연결된 장치:")
            manager.list_connected_devices()
    else:
        print("\n⚠️  저장된 장치가 없습니다.")
        print("처음 사용하시는 경우, 메뉴에서 '1: 새 장치 추가'를 선택해주세요.")
    
    while True:
        print("\n메인 메뉴:")
        print("  1: 새 장치 검색 및 추가")
        print("  2: 저장된 장치 재연결")
        print("  3: 연결된 장치 목록 보기")
        print("  4: 장치 제어 메뉴")
        print("  5: 모든 장치 배터리 확인")
        print("  6: 저장된 장치 목록 보기")
        print("  0: 종료")
        print("\n선택: ", end="")
        
        try:
            choice = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            choice = choice.strip()
            
            if choice == "1":
                # 새 장치 검색 및 추가
                await manager.discover_and_add_devices(timeout=5.0)
            
            elif choice == "2":
                # 저장된 장치 재연결
                await manager.load_and_connect_known_devices()
                if manager.connected_clients:
                    manager.list_connected_devices()
            
            elif choice == "3":
                # 연결된 장치 목록
                manager.list_connected_devices()
            
            elif choice == "4":
                # 장치 제어 메뉴
                if not manager.connected_clients:
                    print("⚠️  연결된 장치가 없습니다.")
                    continue
                
                manager.list_connected_devices()
                print("\n제어할 장치 번호를 입력하세요 (0: 취소): ", end="")
                device_idx = int(input())
                
                if device_idx == 0:
                    continue
                
                device_info = manager.get_device_by_index(device_idx)
                if not device_info:
                    print("⚠️  잘못된 번호입니다.")
                    continue
                
                address, client, name = device_info
                
                # 장치별 제어 루프
                print(f"\n🎛️  {name} 제어 메뉴")
                while True:
                    print("\n사용 가능한 명령:")
                    print("  5: 음소거 토글 🔇/🔊")
                    print("  b: 배터리 정보 확인 🔋")
                    print("  i: 장치 정보 보기")
                    print("  d: 연결 해제")
                    print("  q: 이전 메뉴로")
                    print("\n명령: ", end="")
                    
                    cmd = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                    cmd = cmd.strip()
                    
                    if cmd == "5":
                        await manager.toggle_mute()
                    
                    elif cmd == "b":
                        await manager.get_battery_level(address)
                    
                    elif cmd == "i":
                        await manager.print_device_info(address)
                    
                    elif cmd == "d":
                        await manager.disconnect_device(address)
                        break
                    
                    elif cmd == "q":
                        break
                    
                    else:
                        print(f"알 수 없는 명령: {cmd}")
            
            elif choice == "5":
                # 모든 장치 배터리 확인
                await manager.get_all_battery_levels()
            
            elif choice == "6":
                # 저장된 장치 목록 보기
                if not manager.known_devices:
                    print("⚠️  저장된 장치가 없습니다.")
                else:
                    print("\n💾 저장된 장치 목록:")
                    print("=" * 80)
                    for idx, (address, name) in enumerate(manager.known_devices.items(), 1):
                        connected = "✅ 연결됨" if address in manager.connected_clients else "⚪ 연결 안됨"
                        print(f"{idx}. {name}")
                        print(f"   주소: {address}")
                        print(f"   상태: {connected}")
                        print("-" * 80)
            
            elif choice == "0":
                # 종료
                print("\n종료합니다...")
                await manager.disconnect_all()
                break
            
            else:
                print("잘못된 선택입니다.")
        
        except ValueError:
            print("올바른 숫자를 입력하세요.")
        except KeyboardInterrupt:
            print("\n\n사용자가 중단했습니다.")
            await manager.disconnect_all()
            break
        except Exception as e:
            print(f"오류 발생: {e}")


if __name__ == "__main__":
    asyncio.run(main())

