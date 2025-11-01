"""
행동 감지 결과 → IoT 제어 매핑 로직

Windows로부터 받은 행동 감지 결과를 분석하고
어떤 IoT 기기를 어떻게 제어할지 결정하는 로직
"""
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class ActionDecision:
    """행동 결정 결과"""
    speaker_action: str = None  # "play_alert", "play_normal", "stop", None
    phone_action: str = None    # "notify", "vibrate", "custom", None
    phone_data: Dict[str, Any] = None  # 핸드폰에 전달할 추가 데이터
    confidence: float = 0.0     # 예측 신뢰도
    detected_action: int = 0    # 감지된 행동 ID


class ActionMapper:
    """행동 감지 결과를 분석하여 IoT 제어를 결정하는 클래스"""

    def __init__(self):
        # 행동 ID별 이름 정의
        self.action_names = {
            0: "감지 없음",
            1: "행동 1",
            2: "행동 2",
            3: "행동 3"
        }

        # 행동별 매핑 설정 (커스터마이징 가능)
        self.action_mappings = {
            0: {  # 감지 없음
                "speaker": None,
                "phone": None,
                "description": "아무 동작 안함"
            },
            1: {  # 행동 1 - 높은 경고
                "speaker": "play_alert",
                "phone": "notify",
                "description": "경고음 + 알림"
            },
            2: {  # 행동 2 - 중간 알림
                "speaker": "play_normal",
                "phone": "notify",
                "description": "일반음 + 알림"
            },
            3: {  # 행동 3 - 약한 알림
                "speaker": None,
                "phone": "notify",
                "description": "알림만"
            }
        }

        # 신뢰도 임계값 (이 값보다 낮으면 무시)
        self.confidence_threshold = 0.5

    async def process_and_execute(self, detected_action: int, confidence: float) -> list:
        """
        행동 감지 결과를 분석하고 실제 IoT 제어까지 수행

        Args:
            detected_action: 감지된 행동 ID (0: 없음, 1~3: 행동1~3)
            confidence: 신뢰도 (0.0 ~ 1.0)

        Returns:
            list: 수행된 액션 목록
        """
        # TODO: 실제 Bluetooth 컨트롤러 구현 후 주석 해제
        # from app.services.speaker_controller import speaker_controller
        # from app.services.phone_controller import phone_controller

        action_name = self.action_names.get(detected_action, "알 수 없음")
        print(f"🎯 행동 감지: {action_name} (ID: {detected_action}), 신뢰도: {confidence:.2%}")

        actions_taken = []

        # 신뢰도 체크
        if confidence < self.confidence_threshold:
            print(f"⚪ 신뢰도 낮음 ({confidence:.2%} < {self.confidence_threshold:.2%}) -> 무시")
            return actions_taken

        # 행동 ID가 유효한지 확인
        if detected_action not in self.action_mappings:
            print(f"⚠️ 알 수 없는 행동 ID: {detected_action}")
            return actions_taken

        # 매핑 가져오기
        mapping = self.action_mappings[detected_action]
        print(f"✅ 매핑: {mapping['description']}")

        # 1. 스피커 제어 (임시 응답)
        speaker_action = mapping["speaker"]
        if speaker_action:
            # TODO: 실제 스피커 제어 구현 후 주석 해제
            # if speaker_action == "play_alert":
            #     await speaker_controller.play_alert()
            #     actions_taken.append("speaker:alert")
            # elif speaker_action == "play_normal":
            #     await speaker_controller.play_normal()
            #     actions_taken.append("speaker:normal")
            # elif speaker_action == "stop":
            #     await speaker_controller.stop()
            #     actions_taken.append("speaker:stop")

            # 임시 응답
            print(f"🔊 [임시] 스피커 제어: {speaker_action}")
            actions_taken.append(f"speaker:{speaker_action}")

        # 2. 핸드폰 제어 (임시 응답)
        phone_action = mapping["phone"]
        if phone_action:
            # TODO: 실제 핸드폰 제어 구현 후 주석 해제
            # phone_data = {
            #     "type": f"action_{detected_action}",
            #     "action_name": action_name,
            #     "confidence": confidence,
            #     "description": mapping["description"]
            # }
            #
            # if phone_action == "notify":
            #     await phone_controller.send_notification(
            #         value=confidence,
            #         predicted_class=detected_action
            #     )
            #     actions_taken.append("phone:notify")
            # elif phone_action == "vibrate":
            #     await phone_controller.trigger_vibration()
            #     actions_taken.append("phone:vibrate")
            # elif phone_action == "custom":
            #     await phone_controller.send_custom_command(
            #         command="custom",
            #         data=phone_data
            #     )
            #     actions_taken.append("phone:custom")

            # 임시 응답
            print(f"📱 [임시] 핸드폰 제어: {phone_action}")
            actions_taken.append(f"phone:{phone_action}")

        return actions_taken

    def update_mapping(self, action_id: int, speaker_action: str = None, phone_action: str = None, description: str = None):
        """
        특정 행동 ID의 매핑 설정 변경

        Args:
            action_id: 행동 ID
            speaker_action: 스피커 동작 ("play_alert", "play_normal", None)
            phone_action: 핸드폰 동작 ("notify", "vibrate", None)
            description: 설명
        """
        if action_id not in self.action_mappings:
            print(f"⚠️ 유효하지 않은 행동 ID: {action_id}")
            return

        if speaker_action is not None:
            self.action_mappings[action_id]["speaker"] = speaker_action

        if phone_action is not None:
            self.action_mappings[action_id]["phone"] = phone_action

        if description is not None:
            self.action_mappings[action_id]["description"] = description

        print(f"📝 행동 {action_id} 매핑 업데이트: {self.action_mappings[action_id]}")

    def update_confidence_threshold(self, threshold: float):
        """
        신뢰도 임계값 변경

        Args:
            threshold: 새로운 임계값 (0.0 ~ 1.0)
        """
        self.confidence_threshold = threshold
        print(f"📊 신뢰도 임계값 업데이트: {threshold:.2%}")

    def get_action_info(self, action_id: int) -> dict:
        """
        특정 행동 ID의 정보 조회

        Args:
            action_id: 행동 ID

        Returns:
            dict: 행동 정보
        """
        return {
            "id": action_id,
            "name": self.action_names.get(action_id, "알 수 없음"),
            "mapping": self.action_mappings.get(action_id, {})
        }

    def get_all_mappings(self) -> dict:
        """모든 행동 매핑 정보 반환"""
        return {
            "action_names": self.action_names,
            "action_mappings": self.action_mappings,
            "confidence_threshold": self.confidence_threshold
        }


# 싱글톤 인스턴스
action_mapper = ActionMapper()


# 사용 예시 및 커스터마이징 가이드
if __name__ == "__main__":
    print("=" * 80)
    print("📋 행동 매핑 설정")
    print("=" * 80)

    # 현재 매핑 출력
    mappings = action_mapper.get_all_mappings()
    print("\n현재 매핑:")
    for action_id, mapping in mappings["action_mappings"].items():
        action_name = mappings["action_names"][action_id]
        print(f"  {action_id}. {action_name}: {mapping['description']}")
        print(f"     스피커: {mapping['speaker']}, 핸드폰: {mapping['phone']}")

    print(f"\n신뢰도 임계값: {mappings['confidence_threshold']:.2%}")

    # 테스트
    print("\n" + "=" * 80)
    print("🧪 테스트")
    print("=" * 80)

    # 행동 1 감지 (높은 신뢰도)
    decision = action_mapper.decide_actions(detected_action=1, confidence=0.85)
    print(f"결과: speaker={decision.speaker_action}, phone={decision.phone_action}\n")

    # 행동 2 감지 (중간 신뢰도)
    decision = action_mapper.decide_actions(detected_action=2, confidence=0.65)
    print(f"결과: speaker={decision.speaker_action}, phone={decision.phone_action}\n")

    # 낮은 신뢰도 (무시됨)
    decision = action_mapper.decide_actions(detected_action=1, confidence=0.3)
    print(f"결과: speaker={decision.speaker_action}, phone={decision.phone_action}\n")