"""
NASA IoT Hub - FastAPI 메인 애플리케이션
"""
from fastapi import FastAPI
from app.routers import websocket
from app.services.connection_manager import manager


app = FastAPI(
    title="NASA IoT Hub",
    version="1.0.0",
    description="실시간 딥러닝 IoT 제어 시스템 허브"
)

# WebSocket 라우터 등록
app.include_router(websocket.router)


@app.get("/")
def read_root():
    """API 정보 및 사용 가능한 엔드포인트"""
    return {
        "service": "NASA IoT Hub",
        "version": "1.0.0",
        "description": "WiFi 신호 기반 딥러닝 모델을 통한 실시간 IoT 기기 제어",
        "endpoints": {
            "websocket_windows": "/ws/windows",
            "status": "/status",
            "docs": "/docs"
        }
    }


@app.get("/status")
def get_status():
    """현재 연결 상태 확인"""
    return manager.get_status()


@app.get("/health")
def health_check():
    """헬스 체크"""
    return {"status": "healthy"}