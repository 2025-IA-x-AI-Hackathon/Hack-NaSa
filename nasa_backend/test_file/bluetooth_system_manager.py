"""
macOS 시스템 Bluetooth를 활용한 오디오 장치 관리 및 미디어 제어

필수 도구 설치:
    brew install blueutil
    brew install switchaudio-osx
"""

import asyncio
import subprocess
import sys
import json
import os
from typing import List, Dict, Optional
from bleak import BleakScanner


class BluetoothSystemManager:
    """macOS 시스템 Bluetooth를 사용한 장치 관리 클래스"""
    
    def __init__(self):
        self.known_devices_file = "bluetooth_devices.json"
        self.known_devices: Dict[str, str] = self.load_known_devices()
        self.check_dependencies()
    
    def check_dependencies(self):
        """필요한 시스템 도구가 설치되어 있는지 확인"""
        tools = {
            "blueutil": "brew install blueutil",
            "SwitchAudioSource": "brew install switchaudio-osx"
        }
        
        missing = []
        for tool, install_cmd in tools.items():
            result = subprocess.run(
                ["which", tool],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                missing.append(f"  ❌ {tool} - 설치: {install_cmd}")
        
        if missing:
            print("⚠️  필수 도구가 설치되어 있지 않습니다:")
            for msg in missing:
                print(msg)
            print("\n설치 후 다시 실행해주세요.")
            sys.exit(1)
        else:
            print("✅ 필수 도구 확인 완료")
    
    def load_known_devices(self) -> Dict[str, str]:
        """저장된 장치 목록 로드"""
        if os.path.exists(self.known_devices_file):
            try:
                with open(self.known_devices_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_known_devices(self):
        """장치 목록 저장"""
        try:
            with open(self.known_devices_file, 'w') as f:
                json.dump(self.known_devices, f, indent=2)
        except Exception as e:
            print(f"⚠️  장치 목록 저장 실패: {e}")
    
    def get_paired_devices(self) -> List[Dict[str, str]]:
        """macOS에 페어링된 Bluetooth 장치 목록"""
        try:
            result = subprocess.run(
                ["blueutil", "--paired"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            devices = []
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        # 형식: "address: AA-BB-CC-DD-EE-FF, not connected, not favourite, paired, name: "Device Name", recent access date: ..."
                        parts = line.split(',')
                        address = None
                        name = "Unknown"
                        connected = False
                        
                        for part in parts:
                            part = part.strip()
                            if part.startswith('address:'):
                                address = part.split(':')[1].strip()
                            elif 'name:' in part:
                                name = part.split('name:')[1].strip().strip('"')
                            elif 'connected' in part and 'not' not in part:
                                connected = True
                        
                        if address:
                            devices.append({
                                'address': address,
                                'name': name,
                                'connected': connected
                            })
            
            return devices
            
        except Exception as e:
            print(f"❌ 페어링된 장치 확인 실패: {e}")
            return []
    
    async def scan_ble_devices(self, timeout: float = 5.0) -> List[Dict[str, str]]:
        """BLE 장치 스캔 (추가 장치 발견용)"""
        try:
            print(f"🔍 BLE 장치 스캔 중 ({timeout}초)...")
            
            devices = []
            async with BleakScanner() as scanner:
                await asyncio.sleep(timeout)
                discovered = scanner.discovered_devices_and_advertisement_data
                
                for address, (device, adv_data) in discovered.items():
                    if adv_data.rssi > -70:  # 신호가 강한 장치만
                        name = device.name or "Unknown BLE Device"
                        devices.append({
                            'address': address,
                            'name': name,
                            'connected': False,
                            'type': 'BLE'
                        })
            
            return devices
            
        except Exception as e:
            print(f"❌ BLE 스캔 실패: {e}")
            return []
    
    async def scan_all_devices(self) -> List[Dict[str, str]]:
        """페어링된 장치 + BLE 스캔 결과 통합"""
        print("\n" + "=" * 80)
        print("📱 Bluetooth 장치 검색 중...")
        print("=" * 80)
        
        # 1. 페어링된 장치 (우선 표시)
        paired = self.get_paired_devices()
        
        # 2. BLE 스캔
        ble_devices = await self.scan_ble_devices(timeout=3.0)
        
        # 3. 통합 (중복 제거)
        all_devices = paired.copy()
        paired_addresses = {d['address'] for d in paired}
        
        for ble_dev in ble_devices:
            if ble_dev['address'] not in paired_addresses:
                all_devices.append(ble_dev)
        
        return all_devices
    
    def connect_device(self, address: str, name: str = "Unknown") -> bool:
        """
        macOS 시스템 Bluetooth로 장치 연결
        
        Args:
            address: 장치 MAC 주소 (AA-BB-CC-DD-EE-FF 형식)
            name: 장치 이름
        
        Returns:
            연결 성공 여부
        """
        try:
            print(f"\n📱 '{name}' 연결 중...")
            
            # blueutil로 연결
            result = subprocess.run(
                ["blueutil", "--connect", address],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"✅ '{name}' 연결 성공!")
                
                # 장치 저장
                self.known_devices[address] = name
                self.save_known_devices()
                
                # 잠시 대기 (연결 안정화)
                import time
                time.sleep(2)
                
                return True
            else:
                print(f"❌ 연결 실패: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 연결 중 오류: {e}")
            return False
    
    def disconnect_device(self, address: str, name: str = "Unknown") -> bool:
        """장치 연결 해제"""
        try:
            print(f"\n🔌 '{name}' 연결 해제 중...")
            
            result = subprocess.run(
                ["blueutil", "--disconnect", address],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"✅ '{name}' 연결 해제 완료")
                return True
            else:
                print(f"❌ 연결 해제 실패: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 연결 해제 중 오류: {e}")
            return False
    
    def get_audio_devices(self) -> List[str]:
        """사용 가능한 오디오 출력 장치 목록"""
        try:
            result = subprocess.run(
                ["SwitchAudioSource", "-a", "-t", "output"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                devices = [d.strip() for d in result.stdout.strip().split('\n') if d.strip()]
                return devices
            return []
            
        except Exception as e:
            print(f"❌ 오디오 장치 목록 조회 실패: {e}")
            return []
    
    def switch_audio_output(self, device_name: str) -> bool:
        """오디오 출력을 특정 장치로 전환"""
        try:
            print(f"\n🔊 오디오 출력을 '{device_name}'로 전환 중...")
            
            result = subprocess.run(
                ["SwitchAudioSource", "-s", device_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                print(f"✅ 오디오 출력 전환 완료")
                return True
            else:
                print(f"❌ 오디오 출력 전환 실패")
                return False
                
        except Exception as e:
            print(f"❌ 오디오 출력 전환 중 오류: {e}")
            return False
    
    def media_play_pause(self) -> bool:
        """미디어 재생/일시정지"""
        try:
            # Spotify 제어
            result = subprocess.run(
                ["osascript", "-e", 'tell application "Spotify" to playpause'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("▶️⏸️  재생/일시정지")
                return True
            
            # Apple Music 제어
            result = subprocess.run(
                ["osascript", "-e", 'tell application "Music" to playpause'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("▶️⏸️  재생/일시정지")
                return True
            
            # 미디어 키 대체
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to key code 16'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("▶️⏸️  재생/일시정지")
                return True
            
            print("⚠️  미디어 제어 실패")
            return False
            
        except Exception as e:
            print(f"❌ 미디어 제어 실패: {e}")
            return False
    
    def media_next(self) -> bool:
        """다음 트랙"""
        try:
            # Spotify 제어
            result = subprocess.run(
                ["osascript", "-e", 'tell application "Spotify" to next track'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("⏭️  다음 트랙")
                return True
            
            # Apple Music 제어
            result = subprocess.run(
                ["osascript", "-e", 'tell application "Music" to next track'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("⏭️  다음 트랙")
                return True
            
            # 미디어 키
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to key code 17'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("⏭️  다음 트랙")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ 다음 트랙 실패: {e}")
            return False
    
    def media_previous(self) -> bool:
        """이전 트랙"""
        try:
            # Spotify 제어
            result = subprocess.run(
                ["osascript", "-e", 'tell application "Spotify" to previous track'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("⏮️  이전 트랙")
                return True
            
            # Apple Music 제어
            result = subprocess.run(
                ["osascript", "-e", 'tell application "Music" to previous track'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("⏮️  이전 트랙")
                return True
            
            # 미디어 키
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to key code 18'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                print("⏮️  이전 트랙")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ 이전 트랙 실패: {e}")
            return False


async def main():
    """메인 함수"""
    print("=" * 80)
    print("🎧 macOS Bluetooth 오디오 매니저")
    print("=" * 80)
    
    manager = BluetoothSystemManager()
    
    # 장치 검색
    devices = await manager.scan_all_devices()
    
    if not devices:
        print("\n⚠️  장치를 찾을 수 없습니다.")
        return
    
    # 장치 목록 출력
    print(f"\n발견된 장치: {len(devices)}개")
    print("=" * 80)
    
    for idx, device in enumerate(devices, 1):
        status = "✅ 연결됨" if device.get('connected') else "⚪ 연결 안됨"
        print(f"{idx}. {device['name']}")
        print(f"   주소: {device['address']}")
        print(f"   상태: {status}")
        print("-" * 80)
    
    # 장치 선택
    print("\n연결할 장치 번호를 입력하세요 (0: 취소): ", end="")
    try:
        choice = int(input())
        
        if choice == 0 or choice > len(devices):
            print("취소되었습니다.")
            return
        
        selected = devices[choice - 1]
        
        # 이미 연결된 경우
        if selected.get('connected'):
            print(f"\n✅ '{selected['name']}'는 이미 연결되어 있습니다.")
        else:
            # 연결 시도
            success = manager.connect_device(selected['address'], selected['name'])
            
            if not success:
                print("\n연결에 실패했습니다.")
                return
        
        # 오디오 출력 전환 제안
        audio_devices = manager.get_audio_devices()
        
        if selected['name'] in audio_devices:
            print(f"\n오디오 출력을 '{selected['name']}'로 전환하시겠습니까? (y/n): ", end="")
            if input().strip().lower() == 'y':
                manager.switch_audio_output(selected['name'])
        
        # 미디어 제어 루프
        print("\n" + "=" * 80)
        print("🎵 미디어 제어")
        print("=" * 80)
        print("\n명령어:")
        print("  play  - 재생/일시정지 ▶️⏸️")
        print("  next  - 다음 트랙 ⏭️")
        print("  prev  - 이전 트랙 ⏮️")
        print("  audio - 오디오 출력 장치 변경")
        print("  disc  - 장치 연결 해제")
        print("  q     - 종료")
        
        while True:
            print("\n> ", end="")
            cmd = input().strip().lower()
            
            if cmd == "play":
                manager.media_play_pause()
            
            elif cmd == "next":
                manager.media_next()
            
            elif cmd == "prev":
                manager.media_previous()
            
            elif cmd == "audio":
                print("\n사용 가능한 오디오 출력 장치:")
                audio_devices = manager.get_audio_devices()
                for i, dev in enumerate(audio_devices, 1):
                    print(f"{i}. {dev}")
                print("\n선택 (0: 취소): ", end="")
                try:
                    audio_choice = int(input())
                    if 1 <= audio_choice <= len(audio_devices):
                        manager.switch_audio_output(audio_devices[audio_choice - 1])
                except:
                    print("취소")
            
            elif cmd == "disc":
                manager.disconnect_device(selected['address'], selected['name'])
                break
            
            elif cmd == "q":
                print("종료합니다.")
                break
            
            else:
                print(f"알 수 없는 명령: {cmd}")
    
    except ValueError:
        print("올바른 숫자를 입력하세요.")
    except KeyboardInterrupt:
        print("\n\n종료합니다.")


if __name__ == "__main__":
    asyncio.run(main())

