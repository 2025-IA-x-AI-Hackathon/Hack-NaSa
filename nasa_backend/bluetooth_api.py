"""
FastAPI 서버 - Bluetooth & 미디어 제어 REST API

사용 방법:
    uvicorn bluetooth_api:app --reload --host 0.0.0.0 --port 8000

API 문서:
    http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio

# 기존 클래스 임포트
from bluetooth_universal_manager import BluetoothUniversalManager


# FastAPI 앱 초기화
app = FastAPI(
    title="Bluetooth Media Control API",
    description="macOS Bluetooth 장치 및 미디어 제어 REST API",
    version="1.0.0"
)

# CORS 설정 (모바일 앱에서 호출 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 origin 허용 (프로덕션에서는 제한 필요)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bluetooth 매니저 싱글톤
manager = BluetoothUniversalManager()


# ============================================================================
# Pydantic 모델 (요청/응답 스키마)
# ============================================================================

class DeviceInfo(BaseModel):
    address: str
    name: str
    connected: bool = False

class ConnectRequest(BaseModel):
    address: str
    name: str = "Unknown"

class DisconnectRequest(BaseModel):
    address: str
    name: str = "Unknown"

class AudioSwitchRequest(BaseModel):
    device_name: str

class StatusResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None


# ============================================================================
# API 엔드포인트
# ============================================================================

@app.get("/")
async def root():
    """API 루트 - 상태 확인"""
    return {
        "status": "running",
        "message": "Bluetooth Media Control API",
        "docs": "/docs"
    }


# ----------------------------------------------------------------------------
# 장치 관리
# ----------------------------------------------------------------------------

@app.get("/devices/scan", response_model=StatusResponse)
async def scan_devices():
    """Bluetooth 장치 스캔 (페어링된 장치 + BLE)"""
    try:
        devices = await manager.scan_all_devices()
        
        return StatusResponse(
            success=True,
            message=f"{len(devices)}개 장치 발견",
            data={
                "devices": [
                    {
                        "address": d["address"],
                        "name": d["name"],
                        "connected": d.get("connected", False)
                    }
                    for d in devices
                ]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/devices/paired", response_model=StatusResponse)
async def get_paired_devices():
    """페어링된 장치 목록 조회"""
    try:
        devices = manager.get_paired_devices()
        
        return StatusResponse(
            success=True,
            message=f"{len(devices)}개 페어링된 장치",
            data={
                "devices": devices
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/devices/connect", response_model=StatusResponse)
async def connect_device(request: ConnectRequest):
    """장치 연결"""
    try:
        # 비동기 실행을 위해 run_in_executor 사용
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            manager.connect_device,
            request.address,
            request.name
        )
        
        if success:
            return StatusResponse(
                success=True,
                message=f"'{request.name}' 연결 성공",
                data={"address": request.address, "name": request.name}
            )
        else:
            raise HTTPException(status_code=400, detail="장치 연결 실패")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/devices/disconnect", response_model=StatusResponse)
async def disconnect_device(request: DisconnectRequest):
    """장치 연결 해제"""
    try:
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            manager.disconnect_device,
            request.address,
            request.name
        )
        
        if success:
            return StatusResponse(
                success=True,
                message=f"'{request.name}' 연결 해제 성공"
            )
        else:
            raise HTTPException(status_code=400, detail="연결 해제 실패")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------------
# 오디오 제어
# ----------------------------------------------------------------------------

@app.get("/audio/devices", response_model=StatusResponse)
async def get_audio_devices():
    """사용 가능한 오디오 출력 장치 목록"""
    try:
        devices = manager.get_audio_devices()
        
        return StatusResponse(
            success=True,
            message=f"{len(devices)}개 오디오 장치",
            data={"devices": devices}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audio/switch", response_model=StatusResponse)
async def switch_audio_output(request: AudioSwitchRequest):
    """오디오 출력 장치 전환"""
    try:
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            manager.switch_audio_output,
            request.device_name
        )
        
        if success:
            return StatusResponse(
                success=True,
                message=f"오디오 출력을 '{request.device_name}'로 전환"
            )
        else:
            raise HTTPException(status_code=400, detail="오디오 출력 전환 실패")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------------
# 미디어 제어
# ----------------------------------------------------------------------------

@app.post("/media/play-pause", response_model=StatusResponse)
async def media_play_pause():
    """미디어 재생/일시정지"""
    try:
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, manager.media_play_pause)
        
        if success:
            # 현재 재생 정보 가져오기
            info = await loop.run_in_executor(None, manager.get_now_playing_info)
            
            return StatusResponse(
                success=True,
                message="재생/일시정지 완료",
                data={"now_playing": info} if info else None
            )
        else:
            raise HTTPException(status_code=400, detail="미디어 제어 실패")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/media/next", response_model=StatusResponse)
async def media_next():
    """다음 트랙"""
    try:
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, manager.media_next)
        
        if success:
            # 잠시 대기 후 정보 가져오기
            await asyncio.sleep(0.5)
            info = await loop.run_in_executor(None, manager.get_now_playing_info)
            
            return StatusResponse(
                success=True,
                message="다음 트랙",
                data={"now_playing": info} if info else None
            )
        else:
            raise HTTPException(status_code=400, detail="다음 트랙 실패")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/media/previous", response_model=StatusResponse)
async def media_previous():
    """이전 트랙"""
    try:
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, manager.media_previous)
        
        if success:
            # 잠시 대기 후 정보 가져오기
            await asyncio.sleep(0.5)
            info = await loop.run_in_executor(None, manager.get_now_playing_info)
            
            return StatusResponse(
                success=True,
                message="이전 트랙",
                data={"now_playing": info} if info else None
            )
        else:
            raise HTTPException(status_code=400, detail="이전 트랙 실패")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/media/info", response_model=StatusResponse)
async def media_info():
    """현재 재생 중인 미디어 정보"""
    try:
        loop = asyncio.get_event_loop()
        
        # 각 정보 개별 조회
        title = await loop.run_in_executor(
            None,
            lambda: manager.get_now_playing_info()
        )
        
        if title:
            return StatusResponse(
                success=True,
                message="재생 정보 조회 성공",
                data={"info": title}
            )
        else:
            return StatusResponse(
                success=False,
                message="재생 중인 미디어 없음",
                data={"info": None}
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 서버 시작 (직접 실행 시)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "bluetooth_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

