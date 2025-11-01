"""
블루투스 스피커 제어 서비스

기존 bluetooth_universal_manager.py의 미디어 제어 기능을 래핑
"""
import asyncio
import sys
import os

# 프로젝트 루트 경로 추가 (bluetooth_universal_manager import를 위해)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from bluetooth_universal_manager import BluetoothUniversalManager


class SpeakerController:
    """블루투스 스피커 미디어 제어 클래스"""

    def __init__(self):
        self.bt_manager = BluetoothUniversalManager()
        self.is_initialized = False

    async def initialize(self, device_address: str = None, device_name: str = None):
        """
        스피커 초기화 및 연결

        Args:
            device_address: 블루투스 기기 주소 (선택)
            device_name: 블루투스 기기 이름 (선택)
        """
        try:
            if device_address and device_name:
                # 특정 기기에 연결
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    None,
                    self.bt_manager.connect_device,
                    device_address,
                    device_name
                )

                if success:
                    print(f"✅ 스피커 '{device_name}' 연결 성공")
                    self.is_initialized = True
                else:
                    print(f"⚠️ 스피커 연결 실패, 시스템 기본 출력 사용")
                    self.is_initialized = True
            else:
                # 연결 없이 시스템 기본 미디어 제어만 사용
                print("ℹ️ 시스템 미디어 제어 모드")
                self.is_initialized = True

        except Exception as e:
            print(f"❌ 스피커 초기화 실패: {e}")
            self.is_initialized = False

    async def play_alert(self):
        """경고음 재생 (높은 신뢰도 예측)"""
        try:
            print("🚨 경고음 재생")

            loop = asyncio.get_event_loop()

            # 현재 재생 중인 미디어 일시정지
            await loop.run_in_executor(None, self.bt_manager.media_play_pause)

            # TODO: 실제 경고음 파일 재생 로직 추가
            # 현재는 미디어 제어만 수행

            return True

        except Exception as e:
            print(f"❌ 경고음 재생 실패: {e}")
            return False

    async def play_normal(self):
        """일반 알림음 재생 (중간 신뢰도 예측)"""
        try:
            print("🔔 일반 알림음 재생")

            loop = asyncio.get_event_loop()

            # 간단한 재생/일시정지 토글
            await loop.run_in_executor(None, self.bt_manager.media_play_pause)

            return True

        except Exception as e:
            print(f"❌ 알림음 재생 실패: {e}")
            return False

    async def stop(self):
        """재생 중지"""
        try:
            print("⏹️ 재생 중지")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.bt_manager.media_play_pause)

            return True

        except Exception as e:
            print(f"❌ 중지 실패: {e}")
            return False

    async def get_current_info(self):
        """현재 재생 정보 조회"""
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, self.bt_manager.get_now_playing_info)
            return info

        except Exception as e:
            print(f"❌ 정보 조회 실패: {e}")
            return None

    async def disconnect(self):
        """스피커 연결 해제"""
        try:
            # TODO: 연결된 기기 정보 저장 후 해제 로직 추가
            print("🔌 스피커 연결 해제")
            self.is_initialized = False
            return True

        except Exception as e:
            print(f"❌ 연결 해제 실패: {e}")
            return False


# 싱글톤 인스턴스
speaker_controller = SpeakerController()