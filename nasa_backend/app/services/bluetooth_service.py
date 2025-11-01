import asyncio
from typing import Any, Dict, List, Optional
from app.models.bluetooth_model import DeviceInfo
from app.models.schema import AudioSwitchRequest, ConnectRequest, DisconnectRequest, GattReadRequest, GattWriteRequest
from app.repositories.bluetooth_repository import BluetoothRepository


class BluetoothService:
    """
    비즈니스 로직 처리
    Repository와 Presentation 사이의 중간 계층
    """
    
    def __init__(self, repository: BluetoothRepository):
        self.repo = repository
    
    async def scan_and_get_devices(self) -> List[DeviceInfo]:
        """장치 스캔 및 정보 반환"""
        devices = await self.repo.scan_devices()
        return [DeviceInfo(**device) for device in devices]
    
    def get_paired_devices(self) -> List[DeviceInfo]:
        """페어링된 장치 목록"""
        devices = self.repo.get_paired_devices()
        return [DeviceInfo(**device) for device in devices]
    
    async def connect_to_device(self, request: ConnectRequest) -> tuple[bool, str]:
        """
        장치 연결
        Returns: (success, message)
        """
        # 이미 연결되어 있는지 확인
        if self.repo.is_device_connected(request.address):
            return False, f"'{request.name}'는 이미 연결되어 있습니다."
        
        # 연결 시도
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            self.repo.connect_device,
            request.address,
            request.name
        )
        
        if success:
            # 연결 성공 시 목록에 추가
            device_info = {
                "address": request.address,
                "name": request.name,
                "connected": True
            }
            self.repo.add_connected_device(request.address, device_info)
            return True, f"'{request.name}' 연결 성공"
        
        return False, f"'{request.name}' 연결 실패"
    
    async def disconnect_from_device(self, request: DisconnectRequest) -> tuple[bool, str]:
        """
        장치 연결 해제
        Returns: (success, message)
        """
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            self.repo.disconnect_device,
            request.address,
            request.name
        )
        
        if success:
            self.repo.remove_connected_device(request.address)
            return True, f"'{request.name}' 연결 해제 성공"
        
        return False, f"'{request.name}' 연결 해제 실패"
    
    async def read_gatt_characteristic(self, request: GattReadRequest) -> Optional[str]:
        """GATT 특성 읽기"""
        is_connected = self.repo.is_device_connected(request.address)
        data = await self.repo.read_gatt(
            request.address,
            request.uuid,
            request.name,
            request.ble_address,
            is_connected
        )
        
        if data:
            return data.hex()
        return None
    
    async def write_gatt_characteristic(self, request: GattWriteRequest) -> bool:
        """GATT 특성 쓰기"""
        # hex string을 bytes로 변환
        try:
            if request.data.startswith('0x'):
                data_bytes = bytes.fromhex(request.data[2:])
            else:
                data_bytes = bytes.fromhex(request.data)
        except ValueError as e:
            raise ValueError(f"잘못된 데이터 형식: {e}")
        
        is_connected = self.repo.is_device_connected(request.address)
        return await self.repo.write_gatt(
            request.address,
            request.uuid,
            data_bytes,
            request.name,
            request.ble_address,
            is_connected
        )
    
    async def list_gatt_services(self, address: str, name: str, ble_address: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        GATT 서비스 및 특성 목록 조회 (비즈니스 로직 처리)
        """
        # 1. 입력 유효성 검증
        if not ble_address:
            return {
                "error": "BLE UUID가 없어 GATT 연결을 할 수 없습니다",
                "services": []
            }
        
        # 2. 비즈니스 로직: 시스템 연결 상태 확인 및 처리
        is_connected = self.repo.is_device_connected(address)
        if is_connected:
            # 시스템에 연결되어 있으면 먼저 해제
            self.repo.disconnect_device(address, name)
            await asyncio.sleep(2)
        
        # 3. Repository를 통해 순수 데이터 조회
        services = await self.repo.get_gatt_services_raw(ble_address)
        
        if services is None:
            return {
                "error": "GATT 연결 실패",
                "services": []
            }
        
        # 4. 데이터 변환 및 가공
        try:
            services_data = await self._transform_gatt_services(services, ble_address)
            
            return {
                "device_name": name,
                "device_address": address,
                "ble_address": ble_address,
                "services": services_data,
                "total_services": len(services_data),
                "total_characteristics": sum(len(s["characteristics"]) for s in services_data)
            }
        except Exception as e:
            return {
                "error": f"서비스 탐색 실패: {e}",
                "services": []
            }
    
    async def _transform_gatt_services(self, services, ble_address: str) -> List[Dict[str, Any]]:
        """
        GATT 서비스 데이터를 API 응답 형식으로 변환 (내부 헬퍼 메서드)
        """
        services_data = []
        
        for service in services:
            characteristics_data = []
            
            for char in service.characteristics:
                char_info = {
                    "uuid": str(char.uuid),
                    "handle": char.handle,
                    "description": char.description,
                    "properties": list(char.properties)
                }
                
                # 읽기 가능한 특성이면 값 읽어보기
                if "read" in char.properties:
                    try:
                        value = await self.repo.read_characteristic_value(ble_address, char.handle)
                        if value:
                            char_info["value"] = {
                                "hex": value.hex(),
                                "bytes": list(value),
                                "int": list(value)
                            }
                    except Exception as e:
                        char_info["value"] = None
                        char_info["read_error"] = str(e)
                
                characteristics_data.append(char_info)
            
            services_data.append({
                "uuid": str(service.uuid),
                "description": service.description,
                "characteristics": characteristics_data
            })
        
        return services_data
    
    def get_audio_devices(self) -> List[str]:
        """오디오 장치 목록"""
        return self.repo.get_audio_devices()
    
    async def switch_audio_output(self, request: AudioSwitchRequest) -> tuple[bool, str]:
        """오디오 출력 전환"""
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            self.repo.switch_audio_output,
            request.device_name
        )
        
        if success:
            return True, f"오디오 출력을 '{request.device_name}'로 전환"
        return False, "오디오 출력 전환 실패"
    
    async def control_media_playback(self, action: str) -> tuple[bool, str]:
        """미디어 재생 제어"""
        loop = asyncio.get_event_loop()
        
        if action == "play_pause":
            success = await loop.run_in_executor(None, self.repo.media_play_pause)
            message = "재생/일시정지 완료"
        elif action == "next":
            success = await loop.run_in_executor(None, self.repo.media_next)
            message = "다음 트랙"
        elif action == "previous":
            success = await loop.run_in_executor(None, self.repo.media_previous)
            message = "이전 트랙"
        else:
            return False, f"알 수 없는 액션: {action}"
        
        return success, message if success else f"{message} 실패"
    
    async def get_now_playing(self) -> Optional[str]:
        """현재 재생 정보"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.repo.get_now_playing_info)
    
    def get_connected_devices(self) -> List[DeviceInfo]:
        """연결된 장치 목록"""
        return list(self.repo.get_connected_devices().values())

