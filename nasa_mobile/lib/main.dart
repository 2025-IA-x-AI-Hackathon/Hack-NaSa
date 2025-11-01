import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:nasa_mobile/presentation/views/home.dart';
import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';

@pragma('vm:entry-point')
class MyTaskHandler extends TaskHandler {
  final _ble = FlutterReactiveBle();
  StreamSubscription? _subscription;

  @override
  Future<void> onStart(DateTime timestamp, TaskStarter starter) async {
    // .env 파일 로드
    await dotenv.load(fileName: "assets/.env");
    
    // 백그라운드에서 BLE 특성 구독
    final serviceUuid = dotenv.env['SERVICE_UUID'] ?? 'C9B5CD7A-88A1-6B31-F4C5-38E79F3589CA';
    final characteristicUuid = dotenv.env['CHARACTERISTIC_UUID'] ?? 'C9B5CD7A-88A1-6B31-F4C5-38E79F3589CA';
    
    final characteristic = QualifiedCharacteristic(
      serviceId: Uuid.parse(serviceUuid),
      characteristicId: Uuid.parse(characteristicUuid),
      deviceId: 'YOUR_DEVICE_ID', // 연결된 디바이스 ID
    );

    _subscription = _ble.subscribeToCharacteristic(characteristic).listen((data) {
      // 서버에서 받은 데이터 처리
      _handleServerData(data);
    });
  }

  void _handleServerData(List<int> data) {
    // 예: 첫 바이트가 1이면 알림, 2면 진동 등
    if (data.isNotEmpty) {
      int actionCode = data[0];
      
      switch (actionCode) {
        case 1:
          FlutterForegroundTask.sendDataToMain({'action': 'notification'});
          break;
        case 2:
          FlutterForegroundTask.sendDataToMain({'action': 'vibrate'});
          break;
        // 추가 액션...
      }
    }
  }

  @override
  void onRepeatEvent(DateTime timestamp) {
    // 주기적으로 실행할 작업 (필요시)
  }

  @override
  Future<void> onDestroy(DateTime timestamp, bool killProcess) async {
    await _subscription?.cancel();
  }
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await dotenv.load(fileName: "assets/.env");
  
  FlutterForegroundTask.addTaskDataCallback((data) {
    if (data is Map<String, dynamic>) {
      String? action = data['action'] as String?;
      
      if (action != null) {
        switch (action) {
          case 'notification':
            // 알림 표시
            break;
          case 'vibrate':
            // 진동
            break;
        }
      }
    }
  });
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NaSa Mobile',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blueAccent),
      ),
      home: const HomePage(),
    );
  }
}