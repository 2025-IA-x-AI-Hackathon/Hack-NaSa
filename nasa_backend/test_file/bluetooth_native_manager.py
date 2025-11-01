"""
Pure Core Bluetooth 기반 장치 제어

PyObjC를 사용하여 macOS Core Bluetooth 프레임워크를 직접 사용
bleak, blueutil 등 외부 도구 없이 순수 Core Bluetooth만 사용
"""

import time
import objc
from typing import List, Dict, Optional
from Foundation import NSObject, NSRunLoop, NSDefaultRunLoopMode, NSDate
from CoreBluetooth import (
    CBCentralManager,
    CBPeripheral,
    CBUUID,
    CBCentralManagerStatePoweredOn,
    CBCharacteristicWriteWithResponse,
    CBCharacteristicWriteWithoutResponse
)


class CoreBluetoothDelegate(NSObject):
    """Core Bluetooth 이벤트를 처리하는 Delegate 클래스"""
    
    def init(self):
        self = objc.super(CoreBluetoothDelegate, self).init()
        if self is None:
            return None
        
        self.discovered_peripherals = {}  # {uuid: peripheral}
        self.connected_peripheral = None
        self.discovered_services = []
        self.discovered_characteristics = {}
        self.read_value = None
        self.write_complete = False
        
        return self
    
    # ========================================================================
    # Central Manager Delegates
    # ========================================================================
    
    def centralManagerDidUpdateState_(self, central):
        """Bluetooth 상태 변경"""
        state = central.state()
        
        if state == CBCentralManagerStatePoweredOn:
            print("✅ Bluetooth 활성화됨")
        elif state == 4:  # PoweredOff
            print("❌ Bluetooth 꺼짐")
        elif state == 5:  # Unauthorized
            print("⚠️  Bluetooth 권한 없음")
        else:
            print(f"⚠️  Bluetooth 상태: {state}")
    
    def centralManager_didDiscoverPeripheral_advertisementData_RSSI_(
        self, central, peripheral, advertisementData, rssi
    ):
        """장치 발견"""
        uuid = peripheral.identifier().UUIDString()
        name = peripheral.name() or "Unknown"
        
        self.discovered_peripherals[uuid] = {
            'peripheral': peripheral,
            'name': name,
            'rssi': rssi,
            'uuid': uuid
        }
        
        print(f"📡 발견: {name} (RSSI: {rssi})")
    
    def centralManager_didConnectPeripheral_(self, central, peripheral):
        """장치 연결 성공"""
        name = peripheral.name() or "Unknown"
        print(f"✅ 연결 성공: {name}")
        
        self.connected_peripheral = peripheral
        
        # 서비스 탐색 시작
        print(f"🔍 서비스 탐색 중...")
        peripheral.discoverServices_(None)
    
    def centralManager_didFailToConnectPeripheral_error_(
        self, central, peripheral, error
    ):
        """장치 연결 실패"""
        name = peripheral.name() or "Unknown"
        print(f"❌ 연결 실패: {name}")
        if error:
            print(f"   오류: {error}")
    
    def centralManager_didDisconnectPeripheral_error_(
        self, central, peripheral, error
    ):
        """장치 연결 해제"""
        name = peripheral.name() or "Unknown"
        print(f"🔌 연결 해제: {name}")
        self.connected_peripheral = None
    
    # ========================================================================
    # Peripheral Delegates
    # ========================================================================
    
    def peripheral_didDiscoverServices_(self, peripheral, error):
        """서비스 발견"""
        if error:
            print(f"❌ 서비스 탐색 오류: {error}")
            return
        
        services = peripheral.services()
        print(f"✅ 서비스 {len(services)}개 발견")
        
        self.discovered_services = []
        
        for service in services:
            service_info = {
                'uuid': service.UUID().UUIDString(),
                'peripheral': peripheral,
                'service': service
            }
            self.discovered_services.append(service_info)
            
            print(f"  🔧 {service.UUID().UUIDString()}")
            
            # 각 서비스의 특성 탐색
            peripheral.discoverCharacteristics_forService_(None, service)
    
    def peripheral_didDiscoverCharacteristicsForService_error_(
        self, peripheral, service, error
    ):
        """특성 발견"""
        if error:
            print(f"❌ 특성 탐색 오류: {error}")
            return
        
        service_uuid = service.UUID().UUIDString()
        characteristics = service.characteristics()
        
        print(f"  📋 서비스 {service_uuid}: {len(characteristics)}개 특성")
        
        self.discovered_characteristics[service_uuid] = []
        
        for char in characteristics:
            char_uuid = char.UUID().UUIDString()
            properties = char.properties()
            
            # 속성 파싱
            props = []
            if properties & 0x02:  # Read
                props.append("read")
            if properties & 0x08:  # Write
                props.append("write")
            if properties & 0x04:  # Write without response
                props.append("write-without-response")
            if properties & 0x10:  # Notify
                props.append("notify")
            if properties & 0x20:  # Indicate
                props.append("indicate")
            
            char_info = {
                'uuid': char_uuid,
                'characteristic': char,
                'properties': props,
                'service_uuid': service_uuid
            }
            self.discovered_characteristics[service_uuid].append(char_info)
            
            print(f"    📝 {char_uuid}: {', '.join(props)}")
    
    def peripheral_didUpdateValueForCharacteristic_error_(
        self, peripheral, characteristic, error
    ):
        """특성 값 읽기 완료"""
        if error:
            print(f"❌ 읽기 오류: {error}")
            return
        
        value = characteristic.value()
        if value:
            # NSData를 bytes로 변환
            self.read_value = bytes(value)
            print(f"✅ 값 읽기 성공: {self.read_value}")
        else:
            self.read_value = None
    
    def peripheral_didWriteValueForCharacteristic_error_(
        self, peripheral, characteristic, error
    ):
        """특성 값 쓰기 완료"""
        if error:
            print(f"❌ 쓰기 오류: {error}")
            self.write_complete = False
        else:
            print(f"✅ 쓰기 성공")
            self.write_complete = True


class CoreBluetoothManager:
    """Pure Core Bluetooth 관리자"""
    
    def __init__(self):
        self.delegate = CoreBluetoothDelegate.alloc().init()
        self.central_manager = CBCentralManager.alloc().initWithDelegate_queue_(
            self.delegate, None
        )
        
        # 초기화 대기
        self._wait_for_state(CBCentralManagerStatePoweredOn, timeout=5.0)
    
    def _wait_for_state(self, target_state, timeout=5.0):
        """특정 상태가 될 때까지 대기"""
        start = time.time()
        while time.time() - start < timeout:
            if self.central_manager.state() == target_state:
                return True
            NSRunLoop.currentRunLoop().runMode_beforeDate_(
                NSDefaultRunLoopMode,
                NSDate.dateWithTimeIntervalSinceNow_(0.1)
            )
        return False
    
    def _run_loop(self, duration=0.5):
        """RunLoop 실행 (이벤트 처리)"""
        end_time = time.time() + duration
        while time.time() < end_time:
            NSRunLoop.currentRunLoop().runMode_beforeDate_(
                NSDefaultRunLoopMode,
                NSDate.dateWithTimeIntervalSinceNow_(0.1)
            )
    
    # ========================================================================
    # 장치 스캔
    # ========================================================================
    
    def scan_devices(self, timeout: float = 5.0) -> List[Dict]:
        """
        BLE 장치 스캔
        
        Args:
            timeout: 스캔 시간 (초)
        
        Returns:
            발견된 장치 목록
        """
        print(f"\n🔍 BLE 장치 스캔 중 ({timeout}초)...")
        print("=" * 80)
        
        # 이전 결과 초기화
        self.delegate.discovered_peripherals = {}
        
        # 스캔 시작
        self.central_manager.scanForPeripheralsWithServices_options_(None, None)
        
        # 스캔 시간 동안 RunLoop 실행
        self._run_loop(timeout)
        
        # 스캔 중지
        self.central_manager.stopScan()
        
        devices = list(self.delegate.discovered_peripherals.values())
        print(f"\n✅ {len(devices)}개 장치 발견")
        print("=" * 80)
        
        return devices
    
    def connect_device(self, peripheral_uuid: str) -> bool:
        """
        장치 연결
        
        Args:
            peripheral_uuid: 장치 UUID
        
        Returns:
            연결 성공 여부
        """
        if peripheral_uuid not in self.delegate.discovered_peripherals:
            print(f"⚠️  장치를 찾을 수 없습니다: {peripheral_uuid}")
            return False
        
        peripheral = self.delegate.discovered_peripherals[peripheral_uuid]['peripheral']
        name = peripheral.name() or "Unknown"
        
        print(f"\n📱 '{name}' 연결 중...")
        
        # 연결 시작
        peripheral.setDelegate_(self.delegate)
        self.central_manager.connectPeripheral_options_(peripheral, None)
        
        # 연결 완료 대기
        timeout = 10.0
        start = time.time()
        while time.time() - start < timeout:
            self._run_loop(0.5)
            
            if self.delegate.connected_peripheral is not None:
                # 서비스 탐색 완료 대기
                time.sleep(1)
                self._run_loop(2.0)
                return True
        
        print(f"❌ 연결 타임아웃")
        return False
    
    def disconnect_device(self):
        """현재 연결된 장치 해제"""
        if self.delegate.connected_peripheral is None:
            print("⚠️  연결된 장치가 없습니다")
            return False
        
        peripheral = self.delegate.connected_peripheral
        name = peripheral.name() or "Unknown"
        
        print(f"\n🔌 '{name}' 연결 해제 중...")
        self.central_manager.cancelPeripheralConnection_(peripheral)
        
        self._run_loop(1.0)
        return True
    
    # ========================================================================
    # 서비스 및 특성 조회
    # ========================================================================
    
    def get_services(self) -> List[Dict]:
        """연결된 장치의 서비스 목록"""
        if not self.delegate.connected_peripheral:
            return []
        
        return self.delegate.discovered_services
    
    def get_characteristics(self, service_uuid: str) -> List[Dict]:
        """특정 서비스의 특성 목록"""
        return self.delegate.discovered_characteristics.get(service_uuid, [])
    
    # ========================================================================
    # 특성 읽기/쓰기
    # ========================================================================
    
    def read_characteristic(self, service_uuid: str, char_uuid: str) -> Optional[bytes]:
        """
        특성 값 읽기
        
        Args:
            service_uuid: 서비스 UUID
            char_uuid: 특성 UUID
        
        Returns:
            읽은 데이터 (bytes) 또는 None
        """
        if not self.delegate.connected_peripheral:
            print("⚠️  연결된 장치가 없습니다")
            return None
        
        # 특성 찾기
        chars = self.get_characteristics(service_uuid)
        target_char = None
        
        for char_info in chars:
            if char_uuid.lower() in char_info['uuid'].lower():
                target_char = char_info['characteristic']
                break
        
        if not target_char:
            print(f"⚠️  특성을 찾을 수 없습니다: {char_uuid}")
            return None
        
        # 읽기 권한 확인
        if "read" not in char_info['properties']:
            print(f"⚠️  읽기 불가능한 특성입니다")
            return None
        
        print(f"📖 특성 읽기 중: {char_uuid}")
        
        # 읽기 시작
        self.delegate.read_value = None
        peripheral = self.delegate.connected_peripheral
        peripheral.readValueForCharacteristic_(target_char)
        
        # 읽기 완료 대기
        timeout = 5.0
        start = time.time()
        while time.time() - start < timeout:
            self._run_loop(0.1)
            if self.delegate.read_value is not None:
                return self.delegate.read_value
        
        print(f"❌ 읽기 타임아웃")
        return None
    
    def write_characteristic(
        self, 
        service_uuid: str, 
        char_uuid: str, 
        data: bytes,
        with_response: bool = False
    ) -> bool:
        """
        특성 값 쓰기
        
        Args:
            service_uuid: 서비스 UUID
            char_uuid: 특성 UUID
            data: 쓸 데이터 (bytes)
            with_response: 응답 대기 여부
        
        Returns:
            성공 여부
        """
        if not self.delegate.connected_peripheral:
            print("⚠️  연결된 장치가 없습니다")
            return False
        
        # 특성 찾기
        chars = self.get_characteristics(service_uuid)
        target_char = None
        char_info = None
        
        for ci in chars:
            if char_uuid.lower() in ci['uuid'].lower():
                target_char = ci['characteristic']
                char_info = ci
                break
        
        if not target_char:
            print(f"⚠️  특성을 찾을 수 없습니다: {char_uuid}")
            return False
        
        # 쓰기 권한 확인
        if "write" not in char_info['properties'] and "write-without-response" not in char_info['properties']:
            print(f"⚠️  쓰기 불가능한 특성입니다")
            return False
        
        print(f"✍️  특성 쓰기 중: {char_uuid}")
        
        # NSData 변환
        from Foundation import NSData
        ns_data = NSData.dataWithBytes_length_(data, len(data))
        
        # 쓰기 타입 결정
        write_type = CBCharacteristicWriteWithResponse if with_response else CBCharacteristicWriteWithoutResponse
        
        # 쓰기 시작
        self.delegate.write_complete = False
        peripheral = self.delegate.connected_peripheral
        peripheral.writeValue_forCharacteristic_type_(ns_data, target_char, write_type)
        
        if with_response:
            # 쓰기 완료 대기
            timeout = 5.0
            start = time.time()
            while time.time() - start < timeout:
                self._run_loop(0.1)
                if self.delegate.write_complete:
                    return True
            
            print(f"❌ 쓰기 타임아웃")
            return False
        else:
            # 응답 대기 안함
            self._run_loop(0.2)
            return True
    
    # ========================================================================
    # 고수준 기능
    # ========================================================================
    
    def get_battery_level(self) -> Optional[int]:
        """배터리 레벨 조회 (표준 Battery Service)"""
        # Battery Service UUID
        BATTERY_SERVICE = "0000180f-0000-1000-8000-00805f9b34fb"
        BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"
        
        print("\n🔋 배터리 정보 조회 중...")
        
        value = self.read_characteristic(BATTERY_SERVICE, BATTERY_LEVEL)
        
        if value and len(value) > 0:
            battery_level = value[0]
            
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
        
        print("⚠️  배터리 정보를 읽을 수 없습니다")
        return None
    
    def set_volume(self, volume: int) -> bool:
        """
        볼륨 설정
        
        Args:
            volume: 0-100
        """
        # Volume Service UUID (표준)
        VOLUME_SERVICE = "00001844-0000-1000-8000-00805f9b34fb"
        VOLUME_STATE = "00002b7d-0000-1000-8000-00805f9b34fb"
        
        if not 0 <= volume <= 100:
            print("⚠️  볼륨은 0-100 사이여야 합니다")
            return False
        
        print(f"\n🔊 볼륨 설정: {volume}%")
        
        # 0-255 범위로 변환
        volume_byte = int((volume / 100) * 255)
        data = bytes([volume_byte])
        
        return self.write_characteristic(VOLUME_SERVICE, VOLUME_STATE, data, with_response=False)
    
    def print_all_services(self):
        """모든 서비스 및 특성 출력"""
        if not self.delegate.connected_peripheral:
            print("⚠️  연결된 장치가 없습니다")
            return
        
        print("\n" + "=" * 80)
        print("📋 전체 서비스 및 특성 목록")
        print("=" * 80)
        
        for service in self.delegate.discovered_services:
            service_uuid = service['uuid']
            print(f"\n🔧 서비스: {service_uuid}")
            
            chars = self.get_characteristics(service_uuid)
            for char in chars:
                print(f"  📝 {char['uuid']}")
                print(f"     속성: {', '.join(char['properties'])}")
        
        print("=" * 80)


# ============================================================================
# 메인 함수
# ============================================================================

def main():
    """테스트 메인 함수"""
    print("=" * 80)
    print("🎧 Pure Core Bluetooth 장치 제어")
    print("=" * 80)
    
    manager = CoreBluetoothManager()
    
    # 1. 장치 스캔
    devices = manager.scan_devices(timeout=5.0)
    
    if not devices:
        print("\n⚠️  장치를 찾을 수 없습니다")
        return
    
    # 2. 장치 목록 출력
    print(f"\n발견된 장치:")
    print("=" * 80)
    for idx, device in enumerate(devices, 1):
        print(f"{idx}. {device['name']}")
        print(f"   UUID: {device['uuid']}")
        print(f"   RSSI: {device['rssi']} dBm")
        print("-" * 80)
    
    # 3. 연결할 장치 선택
    print("\n연결할 장치 번호 (0: 취소): ", end="")
    try:
        choice = int(input())
        
        if choice < 1 or choice > len(devices):
            print("취소")
            return
        
        selected = devices[choice - 1]
        
        # 4. 장치 연결
        success = manager.connect_device(selected['uuid'])
        
        if not success:
            print("\n❌ 연결 실패")
            return
        
        # 5. 모든 서비스 및 특성 출력
        manager.print_all_services()
        
        # 6. 배터리 확인
        manager.get_battery_level()
        
        # 7. 제어 루프
        print("\n" + "=" * 80)
        print("🎛️  장치 제어")
        print("=" * 80)
        print("\nCore Bluetooth 명령어:")
        print("  read <service_uuid> <char_uuid> - 특성 읽기")
        print("  write <service_uuid> <char_uuid> <hex_data> - 특성 쓰기")
        print("  battery - 배터리 확인")
        print("  services - 서비스 목록 다시 보기")
        print("  disc - 연결 해제")
        print("  q - 종료")
        print("\n예시:")
        print("  read 0000180f-0000-1000-8000-00805f9b34fb 00002a19-0000-1000-8000-00805f9b34fb")
        print("  write 00001844-0000-1000-8000-00805f9b34fb 00002b7d-0000-1000-8000-00805f9b34fb 50")
        
        while True:
            cmd = input("\n> ").strip().split()
            
            if not cmd:
                continue
            
            if cmd[0] == "q":
                break
            
            elif cmd[0] == "read" and len(cmd) == 3:
                value = manager.read_characteristic(cmd[1], cmd[2])
                if value:
                    print(f"📖 값: {value.hex()} ({list(value)})")
            
            elif cmd[0] == "write" and len(cmd) == 4:
                # hex 데이터 파싱
                hex_str = cmd[3]
                try:
                    if len(hex_str) % 2 == 1:
                        hex_str = "0" + hex_str
                    data = bytes.fromhex(hex_str)
                    manager.write_characteristic(cmd[1], cmd[2], data)
                except ValueError:
                    print("⚠️  올바른 hex 값을 입력하세요 (예: ff, 50, 01ab)")
            
            elif cmd[0] == "battery":
                manager.get_battery_level()
            
            elif cmd[0] == "services":
                manager.print_all_services()
            
            elif cmd[0] == "disc":
                manager.disconnect_device()
                break
            
            else:
                print(f"알 수 없는 명령: {cmd[0]}")
        
        # 연결 해제 (아직 안했으면)
        if manager.delegate.connected_peripheral:
            manager.disconnect_device()
        
        print("\n종료합니다")
    
    except ValueError:
        print("올바른 숫자를 입력하세요")
    except KeyboardInterrupt:
        print("\n\n종료합니다")
        if manager.delegate.connected_peripheral:
            manager.disconnect_device()


if __name__ == "__main__":
    main()

