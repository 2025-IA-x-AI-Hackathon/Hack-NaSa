import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';

class DeviceModel {
  final String id;
  final String name;
  final DeviceConnectionState connectionState;
  final int rssi;
  final List<DiscoveredService> services;

  DeviceModel({
    required this.id,
    this.name = 'Unknown Device',
    this.connectionState = DeviceConnectionState.disconnected,
    this.rssi = 0,
    this.services = const [],
  });

  factory DeviceModel.fromDiscoveredDevice(DiscoveredDevice device) {
    return DeviceModel(
      id: device.id,
      name: device.name.isNotEmpty ? device.name : 'Unknown Device',
      rssi: device.rssi,
    );
  }

  DeviceModel copyWith({
    String? id,
    String? name,
    DeviceConnectionState? connectionState,
    int? rssi,
    List<DiscoveredService>? services,
  }) {
    return DeviceModel(
      id: id ?? this.id,
      name: name ?? this.name,
      connectionState: connectionState ?? this.connectionState,
      rssi: rssi ?? this.rssi,
      services: services ?? this.services,
    );
  }
}