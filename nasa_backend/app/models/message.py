"""
WebSocket 메시지 모델 스키마
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class PredictionMessage(BaseModel):
    """Windows 딥러닝 클라이언트로부터 받는 예측 메시지"""
    type: str = Field(default="prediction", description="메시지 타입")
    result: List[float] = Field(..., description="딥러닝 모델 예측 결과 (예: [0.85, 0.12, 0.03])")
    timestamp: float = Field(..., description="타임스탬프")
    metadata: Optional[dict] = Field(None, description="추가 메타데이터 (선택)")


class ResponseMessage(BaseModel):
    """클라이언트로 보내는 응답 메시지"""
    status: str = Field(..., description="처리 상태 (processed, error)")
    timestamp: float = Field(..., description="응답 타임스탬프")
    message: Optional[str] = Field(None, description="추가 메시지")


class ConnectionInfo(BaseModel):
    """연결 상태 정보"""
    windows_connected: bool = Field(default=False, description="Windows 클라이언트 연결 여부")
    last_message_time: Optional[str] = Field(None, description="마지막 메시지 수신 시간")
    total_messages: int = Field(default=0, description="총 수신 메시지 수")
