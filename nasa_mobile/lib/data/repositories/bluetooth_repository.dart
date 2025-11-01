import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';

abstract class BluetoothRepository {
  Stream<BleStatus> get bleStatusStream;
  
  Stream<DiscoveredDevice> scanForDevices(List<Uuid> serviceUuids);

  Stream<ConnectionStateUpdate> connectToDevice(String deviceId);

  Stream<List<int>> subscribeToCharacteristic(QualifiedCharacteristic characteristic);
}