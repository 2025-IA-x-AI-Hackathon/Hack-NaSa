from typing import Any, Dict, List, Optional
from app.models.bluetooth_model import DeviceInfo
from bluetooth_hybrid_manager import BluetoothHybridManager
from bleak import BleakClient


class BluetoothRepository:
    """
    Bluetooth 매니저와의 인터페이스
    데이터 접근 로직을 캡슐화
    """
    
    def __init__(self):
        self.manager = BluetoothHybridManager()
        self.connected_devices: Dict[str, DeviceInfo] = {}
    
    async def scan_devices(self) -> List[Dict[str, Any]]:
        """장치 스캔"""
        return await self.manager.scan_all_devices()
    
    def get_paired_devices(self) -> List[Dict[str, Any]]:
        """페어링된 장치 조회"""
        return self.manager.get_paired_devices()
    
    def connect_device(self, address: str, name: str) -> bool:
        """장치 연결"""
        return self.manager.connect_device_system(address, name)
    
    def disconnect_device(self, address: str, name: str) -> bool:
        """장치 연결 해제"""
        return self.manager.disconnect_device_system(address, name)
    
    async def read_gatt(
        self,
        address: str,
        uuid: str,
        name: str,
        ble_address: Optional[str],
        is_connected: bool
    ) -> Optional[bytes]:
        """GATT 특성 읽기"""
        return await self.manager.read_gatt_characteristic(
            address=address,
            uuid=uuid,
            name=name,
            ble_address=ble_address,
            is_connected=is_connected
        )
    
    async def write_gatt(
        self,
        address: str,
        uuid: str,
        data: bytes,
        name: str,
        ble_address: Optional[str],
        is_connected: bool
    ) -> bool:
        """GATT 특성 쓰기"""
        return await self.manager.write_gatt_characteristic(
            address=address,
            uuid=uuid,
            data=data,
            name=name,
            ble_address=ble_address,
            is_connected=is_connected
        )
    
    async def get_gatt_services_raw(self, ble_address: str):
        """
        BLE 장치의 GATT 서비스 조회 (순수 데이터 접근)
        Returns: BleakGATTServiceCollection or None
        """
        try:
            client = BleakClient(ble_address, timeout=15.0)
            await client.connect()
            
            if not client.is_connected:
                await client.disconnect()
                return None
            
            services = client.services
            await client.disconnect()
            return services
            
        except Exception as e:
            print(f"GATT 서비스 조회 실패: {e}")
            return None
    
    async def read_characteristic_value(self, ble_address: str, char_handle: int) -> Optional[bytes]:
        """
        특정 Characteristic 값 읽기 (순수 데이터 접근)
        Returns: bytes or None
        """
        try:
            client = BleakClient(ble_address, timeout=15.0)
            await client.connect()
            
            if not client.is_connected:
                await client.disconnect()
                return None
            
            value = await client.read_gatt_char(char_handle)
            await client.disconnect()
            return value
            
        except Exception as e:
            print(f"Characteristic 읽기 실패: {e}")
            return None
    
    def get_audio_devices(self) -> List[str]:
        """오디오 장치 목록"""
        return self.manager.get_audio_devices()
    
    def switch_audio_output(self, device_name: str) -> bool:
        """오디오 출력 전환"""
        return self.manager.switch_audio_output(device_name)
    
    def media_play_pause(self) -> bool:
        """재생/일시정지"""
        return self.manager.media_play_pause()
    
    def media_next(self) -> bool:
        """다음 트랙"""
        return self.manager.media_next()
    
    def media_previous(self) -> bool:
        """이전 트랙"""
        return self.manager.media_previous()
    
    def get_now_playing_info(self) -> Optional[str]:
        """현재 재생 정보"""
        return self.manager.get_now_playing_info()
    
    def add_connected_device(self, address: str, device_info: Dict[str, Any]):
        """연결된 장치 추가"""
        self.connected_devices[address] = DeviceInfo(**device_info)
    
    def remove_connected_device(self, address: str):
        """연결된 장치 제거"""
        if address in self.connected_devices:
            del self.connected_devices[address]
    
    def get_connected_devices(self) -> Dict[str, DeviceInfo]:
        """연결된 장치 목록"""
        return self.connected_devices
    
    def is_device_connected(self, address: str) -> bool:
        """장치 연결 여부 확인"""
        return address in self.connected_devices
