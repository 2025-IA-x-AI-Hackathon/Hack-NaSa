import 'dart:async';
import 'dart:typed_data';
import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';
import 'package:nasa_mobile/data/repositories/bluetooth_repository.dart';

class MockBluetoothRepository implements BluetoothRepository {
  final StreamController<BleStatus> _statusController = StreamController.broadcast();
  final StreamController<ConnectionStateUpdate> _connectionController = StreamController.broadcast();
  final StreamController<List<int>> _characteristicController = StreamController.broadcast();

  MockBluetoothRepository() {
    // BLE 상태를 Ready로 설정
    _statusController.add(BleStatus.ready);
  }

  @override
  Stream<BleStatus> get bleStatusStream => _statusController.stream;

  @override
  Stream<DiscoveredDevice> scanForDevices(List<Uuid> withServices) async* {
    // 가짜 디바이스 목록 반환 (withServices 매개변수는 무시하고 테스트 디바이스 반환)
    await Future.delayed(const Duration(seconds: 1));
    yield DiscoveredDevice(
      id: 'MOCK-DEVICE-001',
      name: 'Mock BLE Server',
      serviceData: {},
      manufacturerData: Uint8List(0),
      rssi: -50,
      serviceUuids: [],
    );
    
    await Future.delayed(const Duration(seconds: 1));
    yield DiscoveredDevice(
      id: 'MOCK-DEVICE-002',
      name: 'Test Device',
      serviceData: {},
      manufacturerData: Uint8List(0),
      rssi: -70,
      serviceUuids: [],
    );
  }

  @override
  Stream<ConnectionStateUpdate> connectToDevice(String deviceId) {
    // 연결 성공 시뮬레이션
    Future.delayed(const Duration(seconds: 2), () {
      _connectionController.add(ConnectionStateUpdate(
        deviceId: deviceId,
        connectionState: DeviceConnectionState.connected,
        failure: null,
      ));
    });

    return _connectionController.stream;
  }

  @override
  Stream<List<int>> subscribeToCharacteristic(
    QualifiedCharacteristic characteristic,
  ) {
    // 주기적으로 테스트 신호 전송 (5초마다)
    Timer.periodic(const Duration(seconds: 5), (timer) {
      // 랜덤하게 액션 코드 전송 (1, 2, 3)
      final actionCode = (timer.tick % 3) + 1;
      _characteristicController.add([actionCode]);
      print('Mock signal sent: action code $actionCode');
    });

    return _characteristicController.stream;
  }

  void dispose() {
    _statusController.close();
    _connectionController.close();
    _characteristicController.close();
  }
}