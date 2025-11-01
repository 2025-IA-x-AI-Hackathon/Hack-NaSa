# Dependency Injection
from typing import Optional
from fastapi import HTTPException
from app.models.schema import ApiResponse, AudioSwitchRequest, ConnectRequest, DisconnectRequest, GattReadRequest, GattWriteRequest
from app.repositories.bluetooth_repository import BluetoothRepository
from app.services.bluetooth_service import BluetoothService
from main import app


repository = BluetoothRepository()
service = BluetoothService(repository)

# ============================================================================
# Presentation Layer (API Routes)
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """API 상태 확인"""
    return {
        "status": "running",
        "message": "Bluetooth Hybrid Control API v2",
        "docs": "/docs"
    }

# ----------------------------------------------------------------------------
# 장치 관리 API
# ----------------------------------------------------------------------------

@app.get("/api/devices/scan", response_model=ApiResponse, tags=["Devices"])
async def scan_devices():
    """Bluetooth 장치 스캔"""
    try:
        devices = await service.scan_and_get_devices()
        
        return ApiResponse(
            success=True,
            message=f"{len(devices)}개 장치 발견",
            data={
                "devices": [device.model_dump() for device in devices],
                "count": len(devices)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/devices/paired", response_model=ApiResponse, tags=["Devices"])
async def get_paired_devices():
    """페어링된 장치 목록"""
    try:
        devices = service.get_paired_devices()
        
        return ApiResponse(
            success=True,
            message=f"{len(devices)}개 페어링된 장치",
            data={
                "devices": [device.model_dump() for device in devices],
                "count": len(devices)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/devices/connected", response_model=ApiResponse, tags=["Devices"])
async def get_connected_devices():
    """현재 연결된 장치 목록"""
    try:
        devices = service.get_connected_devices()
        
        return ApiResponse(
            success=True,
            message=f"{len(devices)}개 연결된 장치",
            data={
                "devices": [device.model_dump() for device in devices],
                "count": len(devices)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/devices/connect", response_model=ApiResponse, tags=["Devices"])
async def connect_device(request: ConnectRequest):
    """장치 연결"""
    try:
        success, message = await service.connect_to_device(request)
        
        if success:
            return ApiResponse(
                success=True,
                message=message,
                data={
                    "address": request.address,
                    "name": request.name
                }
            )
        else:
            raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/devices/disconnect", response_model=ApiResponse, tags=["Devices"])
async def disconnect_device(request: DisconnectRequest):
    """장치 연결 해제"""
    try:
        success, message = await service.disconnect_from_device(request)
        
        if success:
            return ApiResponse(
                success=True,
                message=message
            )
        else:
            raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------------
# GATT 제어 API
# ----------------------------------------------------------------------------

@app.get("/api/gatt/services/{address}", response_model=ApiResponse, tags=["GATT"])
async def list_gatt_services(
    address: str,
    name: str = "Unknown",
    ble_address: Optional[str] = None
):
    """GATT 서비스 및 특성 목록 조회"""
    try:
        services = await service.list_gatt_services(address, name, ble_address)
        
        if services:
            return ApiResponse(
                success=True,
                message=f"GATT 서비스 조회 성공",
                data=services
            )
        else:
            raise HTTPException(status_code=404, detail="서비스 목록을 조회할 수 없습니다")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gatt/read", response_model=ApiResponse, tags=["GATT"])
async def read_gatt_characteristic(request: GattReadRequest):
    """GATT 특성 읽기"""
    try:
        data = await service.read_gatt_characteristic(request)
        
        if data is not None:
            return ApiResponse(
                success=True,
                message="GATT 특성 읽기 성공",
                data={
                    "uuid": request.uuid,
                    "value": data,
                    "address": request.address
                }
            )
        else:
            raise HTTPException(status_code=404, detail="데이터를 읽을 수 없습니다")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gatt/write", response_model=ApiResponse, tags=["GATT"])
async def write_gatt_characteristic(request: GattWriteRequest):
    """GATT 특성 쓰기"""
    try:
        success = await service.write_gatt_characteristic(request)
        
        if success:
            return ApiResponse(
                success=True,
                message="GATT 특성 쓰기 성공",
                data={
                    "uuid": request.uuid,
                    "address": request.address
                }
            )
        else:
            raise HTTPException(status_code=400, detail="데이터를 쓸 수 없습니다")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------------
# 오디오 제어 API
# ----------------------------------------------------------------------------

@app.get("/api/audio/devices", response_model=ApiResponse, tags=["Audio"])
async def get_audio_devices():
    """사용 가능한 오디오 출력 장치 목록"""
    try:
        devices = service.get_audio_devices()
        
        return ApiResponse(
            success=True,
            message=f"{len(devices)}개 오디오 장치",
            data={
                "devices": devices,
                "count": len(devices)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audio/switch", response_model=ApiResponse, tags=["Audio"])
async def switch_audio_output(request: AudioSwitchRequest):
    """오디오 출력 장치 전환"""
    try:
        success, message = await service.switch_audio_output(request)
        
        if success:
            return ApiResponse(
                success=True,
                message=message,
                data={"device": request.device_name}
            )
        else:
            raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------------
# 미디어 제어 API
# ----------------------------------------------------------------------------

@app.post("/api/media/play-pause", response_model=ApiResponse, tags=["Media"])
async def media_play_pause():
    """미디어 재생/일시정지"""
    try:
        success, message = await service.control_media_playback("play_pause")
        
        if success:
            return ApiResponse(success=True, message=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/media/next", response_model=ApiResponse, tags=["Media"])
async def media_next():
    """다음 트랙"""
    try:
        success, message = await service.control_media_playback("next")
        
        if success:
            return ApiResponse(success=True, message=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/media/previous", response_model=ApiResponse, tags=["Media"])
async def media_previous():
    """이전 트랙"""
    try:
        success, message = await service.control_media_playback("previous")
        
        if success:
            return ApiResponse(success=True, message=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/media/info", response_model=ApiResponse, tags=["Media"])
async def get_media_info():
    """현재 재생 중인 미디어 정보"""
    try:
        info = await service.get_now_playing()
        
        if info:
            return ApiResponse(
                success=True,
                message="재생 정보 조회 성공",
                data={"info": info}
            )
        else:
            return ApiResponse(
                success=False,
                message="재생 중인 미디어 없음",
                data={"info": None}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

