import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';
import 'package:nasa_mobile/data/repositories/bluetooth_repository.dart';

class ReactiveBleRepository implements BluetoothRepository {
  final _ble = FlutterReactiveBle();
  
  static final Uuid serviceUuid = Uuid.parse('ABCD'); 
  static final Uuid characteristicUuid = Uuid.parse('EFGH');

  @override
  Stream<BleStatus> get bleStatusStream => _ble.statusStream;

  @override
  Stream<DiscoveredDevice> scanForDevices(List<Uuid> serviceUuids) {
    return _ble.scanForDevices(
      withServices: serviceUuids,
      scanMode: ScanMode.lowLatency,
    );
  }

  @override
  Stream<ConnectionStateUpdate> connectToDevice(String deviceId) {
    return _ble.connectToDevice(
      id: deviceId,
      connectionTimeout: const Duration(seconds: 5), 
    );
  }

  @override
  Stream<List<int>> subscribeToCharacteristic(QualifiedCharacteristic characteristic) {
    return _ble.subscribeToCharacteristic(characteristic);
  }
}