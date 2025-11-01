import 'dart:async';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';
import 'package:nasa_mobile/data/repositories/bluetooth_repository.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class ActionViewModel with ChangeNotifier {
  final BluetoothRepository _repository;
  StreamSubscription? _statusSubscription;
  StreamSubscription? _connectionSubscription;
  final AudioPlayer _audioPlayer = AudioPlayer();
  
  String? _connectedDeviceId; 
  String? get connectedDeviceId => _connectedDeviceId;

  ActionViewModel(this._repository) {
    _initAudioPlayer();
    _statusSubscription = _repository.bleStatusStream.listen((status) {
      if (status == BleStatus.ready) {
      }
      notifyListeners();
    });
  }

  void _initAudioPlayer() async {
    // 시스템 볼륨 무시하고 최대 볼륨으로 재생
    await _audioPlayer.setVolume(1.0);
    // 오디오 세션 모드 설정 (iOS)
    await _audioPlayer.setAudioContext(
      AudioContext(
        iOS: AudioContextIOS(
          category: AVAudioSessionCategory.playback,
          options: {
            AVAudioSessionOptions.mixWithOthers,
            AVAudioSessionOptions.duckOthers,
          },
        ),
        android: AudioContextAndroid(
          isSpeakerphoneOn: true,
          stayAwake: true,
          contentType: AndroidContentType.music,
          usageType: AndroidUsageType.alarm,
          audioFocus: AndroidAudioFocus.gain,
        ),
      ),
    );
  }

  Future<void> playAlarmSound() async {
    try {
      await _audioPlayer.play(AssetSource('sounds/sound1.wav'));
      debugPrint('Alarm sound played successfully.');
    } catch (e) {
      debugPrint('Failed to play alarm sound: $e');
    }
  }

  Future<void> playAlarmSoundLoop() async {
    try {
      await _audioPlayer.setReleaseMode(ReleaseMode.loop);
      await _audioPlayer.play(AssetSource('sounds/sound1.wav'));
      debugPrint('Alarm sound loop started.');
    } catch (e) {
      debugPrint('Failed to play alarm sound loop: $e');
    }
  }

  Future<void> stopAlarmSound() async {
    try {
      await _audioPlayer.stop();
      debugPrint('Alarm sound stopped.');
    } catch (e) {
      debugPrint('Failed to stop alarm sound: $e');
    }
  }

  void connectAndStartForegroundTask(DiscoveredDevice device) async {
    _connectedDeviceId = device.id;
    notifyListeners();

    _connectionSubscription?.cancel();
    _connectionSubscription = _repository.connectToDevice(device.id).listen((update) {
      if (update.connectionState == DeviceConnectionState.connected) {
        _startForegroundService();
        _subscribeToServerData(device.id);
      }
    });
  }

  void connectToMockDevice() {
    final mockDevice = DiscoveredDevice(
      id: 'MOCK-DEVICE-001',
      name: 'Mock BLE Server',
      serviceData: {},
      manufacturerData: Uint8List(0),
      rssi: -50,
      serviceUuids: [],
    );
    
    connectAndStartForegroundTask(mockDevice);
  }

  void _subscribeToServerData(String deviceId) {
    // .env 파일에서 UUID 가져오기
    final serviceUuid = dotenv.env['SERVICE_UUID'] ?? 'C9B5CD7A-88A1-6B31-F4C5-38E79F3589CA';
    final characteristicUuid = dotenv.env['CHARACTERISTIC_UUID'] ?? 'C9B5CD7A-88A1-6B31-F4C5-38E79F3589CA';
    
    final characteristic = QualifiedCharacteristic(
      serviceId: Uuid.parse(serviceUuid),
      characteristicId: Uuid.parse(characteristicUuid),
      deviceId: deviceId,
    );

    _repository.subscribeToCharacteristic(characteristic).listen((data) {
      _processServerSignal(data);
    });
  }

  void _processServerSignal(List<int> data) {
    if (data.isNotEmpty) {
      int actionCode = data[0];
      
      switch (actionCode) {
        case 1:
          playAlarmSound();
          break;
        case 2:
          playAlarmSoundLoop();
          break;
        case 3:
          stopAlarmSound();
          break;
        default:
          debugPrint('Unknown action code: $actionCode');
      }
      
      notifyListeners();
    }
  }

  void _startForegroundService() async {
    try {
      await FlutterForegroundTask.startService(
        notificationTitle: 'Hackathon Service Running',
        notificationText: '블루투스 신호를 감지하고 있습니다.',
      );
      debugPrint('Foreground service started successfully.');
    } catch (e) {
      debugPrint('Failed to start foreground service: $e');
    }
  }

  @override
  void dispose() {
    _statusSubscription?.cancel();
    _connectionSubscription?.cancel();
    _audioPlayer.dispose();
    FlutterForegroundTask.stopService();
    super.dispose();
  }
}