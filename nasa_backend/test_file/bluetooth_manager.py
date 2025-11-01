import asyncio
from bleak import BleakScanner, BleakClient
from typing import Optional, List
import sys
import subprocess


class BluetoothManager:
    """Bluetooth 장치를 스캔하고 연결을 관리하는 클래스"""
    
    def __init__(self):
        self.connected_client: Optional[BleakClient] = None
        self.device_address: Optional[str] = None
    
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
    
    async def connect_device(self, address: str) -> bool:
        """
        특정 주소의 Bluetooth 장치에 연결합니다.
        
        Args:
            address: 연결할 장치의 MAC 주소
        
        Returns:
            연결 성공 여부
        """
        try:
            print(f"\n📱 장치에 연결 중: {address}")
            self.connected_client = BleakClient(address)
            await self.connected_client.connect()
            self.device_address = address
            
            if self.connected_client.is_connected:
                print(f"✅ 연결 성공!")
                await self.print_device_info()
                return True
            else:
                print("❌ 연결 실패")
                return False
                
        except Exception as e:
            print(f"❌ 연결 중 오류 발생: {e}")
            return False
    
    async def disconnect_device(self):
        """현재 연결된 장치와의 연결을 끊습니다."""
        if self.connected_client and self.connected_client.is_connected:
            await self.connected_client.disconnect()
            print(f"🔌 장치 연결 해제됨: {self.device_address}")
            self.connected_client = None
            self.device_address = None
        else:
            print("⚠️  연결된 장치가 없습니다.")
    
    async def print_device_info(self):
        """연결된 장치의 서비스와 특성 정보를 출력합니다."""
        if not self.connected_client or not self.connected_client.is_connected:
            print("⚠️  연결된 장치가 없습니다.")
            return
        
        print("\n📋 장치 서비스 및 특성 정보:")
        print("=" * 80)
        
        services = self.connected_client.services
        for service in services:
            print(f"\n🔧 서비스: {service.uuid}")
            print(f"   설명: {service.description}")
            
            for char in service.characteristics:
                print(f"\n   📝 특성: {char.uuid}")
                print(f"      핸들: {char.handle}")
                print(f"      속성: {', '.join(char.properties)}")
                
                if "read" in char.properties:
                    try:
                        # handle을 사용하여 특성 값 읽기 (UUID가 중복될 수 있음)
                        value = await self.connected_client.read_gatt_char(char.handle)
                        print(f"      값: {value}")
                    except Exception as e:
                        print(f"      값 읽기 실패: {e}")
        
        print("=" * 80)
    
    async def read_characteristic(self, char_uuid: str) -> Optional[bytes]:
        """
        특정 특성(characteristic)의 값을 읽습니다.
        
        Args:
            char_uuid: 특성의 UUID
        
        Returns:
            읽은 데이터 (bytes) 또는 None
        """
        if not self.connected_client or not self.connected_client.is_connected:
            print("⚠️  연결된 장치가 없습니다.")
            return None
        
        try:
            value = await self.connected_client.read_gatt_char(char_uuid)
            print(f"📖 특성 {char_uuid} 읽기 성공: {value}")
            return value
        except Exception as e:
            print(f"❌ 특성 읽기 실패: {e}")
            return None
    
    async def write_characteristic(self, char_uuid: str, data: bytes) -> bool:
        """
        특정 특성(characteristic)에 값을 씁니다.
        
        Args:
            char_uuid: 특성의 UUID
            data: 쓸 데이터 (bytes)
        
        Returns:
            쓰기 성공 여부
        """
        if not self.connected_client or not self.connected_client.is_connected:
            print("⚠️  연결된 장치가 없습니다.")
            return False
        
        try:
            await self.connected_client.write_gatt_char(char_uuid, data)
            print(f"✍️  특성 {char_uuid} 쓰기 성공")
            return True
        except Exception as e:
            print(f"❌ 특성 쓰기 실패: {e}")
            return False
    
    def is_connected(self) -> bool:
        """현재 장치 연결 상태를 반환합니다."""
        return self.connected_client is not None and self.connected_client.is_connected
    
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
    
    def media_play_pause(self) -> bool:
        """
        macOS 시스템에서 현재 재생 중인 미디어를 재생/일시정지합니다.
        모든 앱(Spotify, YouTube, Safari, Chrome 등)을 지원합니다.
        
        Returns:
            명령 실행 성공 여부
        """
        try:
            print("▶️⏸️  미디어 재생/일시정지...")
            
            # 방법 1: nowplayingctl 사용 (macOS Big Sur 이상, 가장 확실)
            result = subprocess.run(
                ["bash", "-c", "nowplayingctl toggle 2>/dev/null || exit 1"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("✅ 재생/일시정지 완료")
                return True
            
            # 방법 2: 미디어 키 시뮬레이션 (호환성 높음)
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to key code 16'],
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
    
    def media_next_track(self) -> bool:
        """
        다음 트랙으로 이동합니다.
        모든 미디어 앱을 지원합니다.
        
        Returns:
            명령 실행 성공 여부
        """
        try:
            print("⏭️  다음 트랙...")
            
            # 방법 1: nowplayingctl 사용
            result = subprocess.run(
                ["bash", "-c", "nowplayingctl next 2>/dev/null || exit 1"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("✅ 다음 트랙")
                return True
            
            # 방법 2: 미디어 키 시뮬레이션
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to key code 17'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("✅ 다음 트랙")
                return True
            
            print("⚠️  미디어 제어 실패")
            return False
            
        except Exception as e:
            print(f"❌ 다음 트랙 제어 실패: {e}")
            return False
    
    def media_previous_track(self) -> bool:
        """
        이전 트랙으로 이동합니다.
        모든 미디어 앱을 지원합니다.
        
        Returns:
            명령 실행 성공 여부
        """
        try:
            print("⏮️  이전 트랙...")
            
            # 방법 1: nowplayingctl 사용
            result = subprocess.run(
                ["bash", "-c", "nowplayingctl previous 2>/dev/null || exit 1"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("✅ 이전 트랙")
                return True
            
            # 방법 2: 미디어 키 시뮬레이션
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to key code 18'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("✅ 이전 트랙")
                return True
            
            print("⚠️  미디어 제어 실패")
            return False
            
        except Exception as e:
            print(f"❌ 이전 트랙 제어 실패: {e}")
            return False
    
    async def get_battery_level(self) -> Optional[int]:
        """
        Bluetooth 장치의 배터리 레벨을 가져옵니다.
        
        Returns:
            배터리 퍼센트 (0-100) 또는 None
        """
        if not self.connected_client or not self.connected_client.is_connected:
            print("⚠️  연결된 장치가 없습니다.")
            return None
        
        try:
            # 표준 Battery Service UUID
            BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
            BATTERY_LEVEL_CHAR_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
            
            print("🔋 배터리 정보를 요청합니다...")
            
            # 배터리 서비스 찾기
            services = self.connected_client.services
            battery_service = None
            
            for service in services:
                if BATTERY_SERVICE_UUID.lower() in service.uuid.lower():
                    battery_service = service
                    break
            
            if not battery_service:
                print("⚠️  배터리 서비스를 찾을 수 없습니다.")
                # 모든 서비스에서 배터리 레벨 특성 찾기 시도
                for service in services:
                    for char in service.characteristics:
                        if BATTERY_LEVEL_CHAR_UUID.lower() in char.uuid.lower():
                            try:
                                value = await self.connected_client.read_gatt_char(char.handle)
                                battery_level = int(value[0])
                                print(f"🔋 배터리: {battery_level}%")
                                return battery_level
                            except Exception as e:
                                print(f"배터리 정보 읽기 실패: {e}")
                return None
            
            # 배터리 레벨 특성 찾기
            for char in battery_service.characteristics:
                if BATTERY_LEVEL_CHAR_UUID.lower() in char.uuid.lower():
                    try:
                        value = await self.connected_client.read_gatt_char(char.handle)
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
                        
                        print(f"{emoji} 배터리: {battery_level}%")
                        return battery_level
                    except Exception as e:
                        print(f"❌ 배터리 정보 읽기 실패: {e}")
                        return None
            
            print("⚠️  배터리 레벨 특성을 찾을 수 없습니다.")
            return None
            
        except Exception as e:
            print(f"❌ 배터리 정보 조회 실패: {e}")
            return None
    
    async def find_writable_characteristics(self):
        """쓰기 가능한 모든 특성을 찾아 출력합니다."""
        if not self.connected_client or not self.connected_client.is_connected:
            print("⚠️  연결된 장치가 없습니다.")
            return
        
        print("\n📝 쓰기 가능한 특성 목록:")
        print("=" * 80)
        
        services = self.connected_client.services
        for service in services:
            has_writable = False
            writable_chars = []
            
            for char in service.characteristics:
                if "write" in char.properties or "write-without-response" in char.properties:
                    has_writable = True
                    writable_chars.append(char)
            
            if has_writable:
                print(f"\n🔧 서비스: {service.uuid}")
                print(f"   설명: {service.description}")
                
                for char in writable_chars:
                    print(f"\n   📝 특성: {char.uuid}")
                    print(f"      핸들: {char.handle}")
                    print(f"      속성: {', '.join(char.properties)}")
        
        print("=" * 80)


async def main():
    """테스트용 메인 함수"""
    manager = BluetoothManager()
    
    # 1. 장치 스캔
    devices = await manager.scan_devices(timeout=5.0)
    
    if not devices:
        print("스캔된 장치가 없습니다.")
        return
    
    # 2. 연결할 장치 선택
    print("\n연결할 장치 번호를 입력하세요 (0: 취소): ", end="")
    try:
        choice = int(input())
        if choice == 0 or choice > len(devices):
            print("취소되었습니다.")
            return
        
        selected_device = devices[choice - 1]
        
        # 3. 장치 연결
        connected = await manager.connect_device(selected_device["address"])
        
        if connected:
            print("\n✅ 이어폰이 연결되었습니다!")
            print("\n사용 가능한 명령:")
            print("  play  : 음악 재생/일시정지 ▶️⏸️")
            print("  next  : 다음 트랙 ⏭️")
            print("  prev  : 이전 트랙 ⏮️")
            print("  5     : 음소거 토글 🔇/🔊")
            print("  b     : 배터리 정보 확인 🔋")
            print("  w     : 쓰기 가능한 특성 보기")
            print("  q     : 종료")
            print("\n명령을 입력하세요: ", end="")
            
            # 명령 입력 루프
            loop = asyncio.get_event_loop()
            
            try:
                while manager.is_connected():
                    # 비동기적으로 사용자 입력 받기
                    cmd = await loop.run_in_executor(None, sys.stdin.readline)
                    cmd = cmd.strip().lower()
                    
                    if cmd == "play":
                        manager.media_play_pause()
                        print("\n명령을 입력하세요: ", end="")
                    
                    elif cmd == "next":
                        manager.media_next_track()
                        print("\n명령을 입력하세요: ", end="")
                    
                    elif cmd == "prev":
                        manager.media_previous_track()
                        print("\n명령을 입력하세요: ", end="")
                    
                    elif cmd == "5":
                        await manager.toggle_mute()
                        print("\n명령을 입력하세요: ", end="")
                    
                    elif cmd == "b":
                        await manager.get_battery_level()
                        print("\n명령을 입력하세요: ", end="")
                    
                    elif cmd == "w":
                        await manager.find_writable_characteristics()
                        print("\n명령을 입력하세요: ", end="")
                    
                    elif cmd == "q":
                        print("종료합니다...")
                        await manager.disconnect_device()
                        break
                    
                    else:
                        print(f"알 수 없는 명령: {cmd}")
                        print("사용 가능한 명령: play (재생/정지), next (다음), prev (이전), 5 (음소거), b (배터리), w (특성), q (종료)")
                        print("\n명령을 입력하세요: ", end="")
                        
            except KeyboardInterrupt:
                print("\n\n사용자가 중단했습니다.")
                await manager.disconnect_device()
    
    except ValueError:
        print("올바른 숫자를 입력하세요.")
    except KeyboardInterrupt:
        print("\n\n사용자가 중단했습니다.")
        if manager.is_connected():
            await manager.disconnect_device()


if __name__ == "__main__":
    asyncio.run(main())

