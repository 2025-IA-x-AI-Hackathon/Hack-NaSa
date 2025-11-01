"""
WebSocket 라우터
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.connection_manager import manager
from app.models.message import PredictionMessage
import json


router = APIRouter()


@router.websocket("/ws/windows")
async def websocket_windows_endpoint(websocket: WebSocket):
    """
    Windows 딥러닝 클라이언트 WebSocket 엔드포인트

    - Windows로부터 실시간 예측 결과 수신
    - 처리 결과 응답 전송
    """
    await manager.connect_windows(websocket)

    try:
        while True:
            # Windows로부터 메시지 수신
            data = await websocket.receive_text()
            message_dict = json.loads(data)

            # Pydantic 모델로 변환 및 검증
            # TODO: 데이터 수신 형식 확인
            prediction_message = PredictionMessage(**message_dict)

            # 예측 결과 처리
            response = await manager.process_prediction(prediction_message)

            # 처리 결과 응답
            await websocket.send_json(response.model_dump())

    except WebSocketDisconnect:
        manager.disconnect_windows(websocket)
        print("🔌 WebSocket 정상 종료")
    except Exception as e:
        print(f"⚠️ 에러 발생: {e}")
        manager.disconnect_windows(websocket)