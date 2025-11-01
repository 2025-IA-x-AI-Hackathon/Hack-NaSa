from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DeviceStatus(str, Enum):
    """장치 상태"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"


class DeviceInfo(BaseModel):
    """장치 정보"""
    address: str = Field(..., description="장치 MAC 주소 또는 BLE UUID")
    name: str = Field(..., description="장치 이름")
    connected: bool = Field(False, description="시스템 연결 여부")
    ble_address: Optional[str] = Field(None, description="BLE UUID (있는 경우)")
    ble_addresses_all: Optional[List[str]] = Field(None, description="여러 BLE UUID (있는 경우)")
