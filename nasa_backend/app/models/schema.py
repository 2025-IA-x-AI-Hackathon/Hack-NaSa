from typing import Any, Optional
from pydantic import BaseModel, Field


class ConnectRequest(BaseModel):
    """연결 요청"""
    address: str = Field(..., description="장치 MAC 주소 또는 BLE UUID")
    name: str = Field("Unknown", description="장치 이름")


class DisconnectRequest(BaseModel):
    """연결 해제 요청"""
    address: str = Field(..., description="장치 MAC 주소")
    name: str = Field("Unknown", description="장치 이름")


class GattReadRequest(BaseModel):
    """GATT 읽기 요청"""
    address: str = Field(..., description="장치 MAC 주소")
    uuid: str = Field(..., description="특성 UUID (예: 00002a19-0000-1000-8000-00805f9b34fb)")
    name: str = Field("Unknown", description="장치 이름")
    ble_address: Optional[str] = Field(None, description="BLE UUID")


class GattWriteRequest(BaseModel):
    """GATT 쓰기 요청"""
    address: str = Field(..., description="장치 MAC 주소")
    uuid: str = Field(..., description="특성 UUID")
    data: str = Field(..., description="쓸 데이터 (hex string, 예: '0x01')")
    name: str = Field("Unknown", description="장치 이름")
    ble_address: Optional[str] = Field(None, description="BLE UUID")


class AudioSwitchRequest(BaseModel):
    """오디오 출력 전환 요청"""
    device_name: str = Field(..., description="오디오 장치 이름")


class ApiResponse(BaseModel):
    """API 응답"""
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    data: Optional[Any] = Field(None, description="응답 데이터")

