"""
핸드폰 블루투스 제어 서비스

안드로이드 기기와 블루투스로 통신하여 알림, 진동 등을 제어
"""
import asyncio
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from bluetooth_universal_manager import BluetoothUniversalManager


class PhoneController:
    """안드로이드 핸드폰 블루투스 제어 클래스"""

    def __init__(self):
        self.bt_manager = BluetoothUniversalManager()
        self.is_connected = False
        self.phone_address = None
        self.phone_name = None

    async def connect(self, device_address: str, device_name: str = "Android Phone"):
        """
        안드로이드 기기에 연결

        Args:
            device_address: 블루투스 기기 주소
            device_name: 블루투스 기기 이름
        """
        try:
            print(f"📱 안드로이드 '{device_name}' 연결 시도...")

            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self.bt_manager.connect_device,
                device_address,
                device_name
            )

            if success:
                self.is_connected = True
                self.phone_address = device_address
                self.phone_name = device_name
                print(f"✅ 안드로이드 '{device_name}' 연결 성공")
                return True
            else:
                print(f"❌ 안드로이드 연결 실패")
                return False

        except Exception as e:
            print(f"❌ 안드로이드 연결 중 오류: {e}")
            return False

    async def send_notification(self, value: float, predicted_class: int = None):
        """
        안드로이드에 알림 전송

        Args:
            value: 예측 신뢰도 값 (0.0 ~ 1.0)
            predicted_class: 예측된 클래스 인덱스
        """
        try:
            if not self.is_connected:
                print("⚠️ 안드로이드 연결되지 않음")
                return False

            print(f"📲 안드로이드 알림 전송 - 신뢰도: {value:.2f}")

            # TODO: 실제 블루투스 데이터 전송 로직 구현
            # 현재는 로그만 출력

            if predicted_class is not None:
                print(f"   예측 클래스: {predicted_class}")

            return True

        except Exception as e:
            print(f"❌ 알림 전송 실패: {e}")
            return False

    async def trigger_vibration(self, duration_ms: int = 200):
        """
        안드로이드 진동 트리거

        Args:
            duration_ms: 진동 지속 시간 (밀리초)
        """
        try:
            if not self.is_connected:
                print("⚠️ 안드로이드 연결되지 않음")
                return False

            print(f"📳 안드로이드 진동 트리거 ({duration_ms}ms)")

            # TODO: 실제 블루투스 진동 명령 전송 로직 구현

            return True

        except Exception as e:
            print(f"❌ 진동 트리거 실패: {e}")
            return False

    async def send_custom_command(self, command: str, data: dict = None):
        """
        커스텀 명령 전송

        Args:
            command: 명령 타입 (예: "alert", "update", "clear")
            data: 추가 데이터
        """
        try:
            if not self.is_connected:
                print("⚠️ 안드로이드 연결되지 않음")
                return False

            print(f"📤 안드로이드 커스텀 명령 전송: {command}")
            if data:
                print(f"   데이터: {data}")

            # TODO: 실제 블루투스 커스텀 명령 전송 로직 구현

            return True

        except Exception as e:
            print(f"❌ 커스텀 명령 전송 실패: {e}")
            return False

    async def disconnect(self):
        """안드로이드 연결 해제"""
        try:
            if not self.is_connected or not self.phone_address:
                print("ℹ️ 연결된 안드로이드 없음")
                return True

            print(f"🔌 안드로이드 '{self.phone_name}' 연결 해제 중...")

            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self.bt_manager.disconnect_device,
                self.phone_address,
                self.phone_name
            )

            if success:
                self.is_connected = False
                self.phone_address = None
                self.phone_name = None
                print("✅ 안드로이드 연결 해제 완료")
                return True
            else:
                print("⚠️ 연결 해제 실패")
                return False

        except Exception as e:
            print(f"❌ 연결 해제 중 오류: {e}")
            return False

    def get_status(self) -> dict:
        """현재 연결 상태 반환"""
        return {
            "connected": self.is_connected,
            "device_address": self.phone_address,
            "device_name": self.phone_name
        }


# 싱글톤 인스턴스
phone_controller = PhoneController()