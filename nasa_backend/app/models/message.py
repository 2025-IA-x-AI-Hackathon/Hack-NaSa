"""
WebSocket 메시지 모델 스키마
"""
from pydantic import BaseModel, Field
from typing import Optional


class PredictionMessage(BaseModel):
    """Windows 딥러닝 클라이언트로부터 받는 예측 메시지"""
    type: str = Field(default="prediction", description="메시지 타입")
    detected_action: int = Field(..., description="감지된 행동 ID (0: 감지 없음, 1: 행동1, 2: 행동2, 3: 행동3)")
    confidence: float = Field(..., description="신뢰도 (0.0 ~ 1.0)")
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
