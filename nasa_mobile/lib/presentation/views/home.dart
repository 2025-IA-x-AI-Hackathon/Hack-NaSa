import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:nasa_mobile/presentation/view_models/action_view_model.dart';
import 'package:nasa_mobile/data/repositories/reactive_ble_repository.dart';
import 'package:nasa_mobile/data/repositories/mock_bluetooth_repository.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<HomePage> {
  late ActionViewModel _viewModel;
  bool _useMockBle = true; // Mock 모드 기본값

  @override
  void initState() {
    super.initState();
    _initViewModel();
  }

  void _initViewModel() {
    if (_useMockBle) {
      _viewModel = ActionViewModel(MockBluetoothRepository());
    } else {
      _viewModel = ActionViewModel(ReactiveBleRepository());
    }
  }

  void _toggleMockMode(bool value) {
    setState(() {
      _useMockBle = value;
      _viewModel.dispose();
      _initViewModel();
    });
  }

  @override
  void dispose() {
    _viewModel.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: _viewModel,
      child: Scaffold(
        appBar: AppBar(
          backgroundColor: Theme.of(context).colorScheme.inversePrimary,
          title: const Text('NaSa Mobile Home Page'),
        ),
        body: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Mock 모드 토글
                Card(
                  color: _useMockBle ? Colors.orange.shade50 : Colors.blue.shade50,
                  elevation: 4,
                  child: SwitchListTile(
                    title: Text(
                      _useMockBle ? '🧪 Mock 테스트 모드' : '📡 실제 BLE 모드',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                      ),
                    ),
                    subtitle: Text(
                      _useMockBle 
                          ? '가짜 BLE 신호로 테스트 (실제 디바이스 불필요)'
                          : '실제 BLE 디바이스와 연결',
                      style: const TextStyle(fontSize: 13),
                    ),
                    value: _useMockBle,
                    onChanged: _toggleMockMode,
                    activeThumbColor: Colors.orange,
                    secondary: Icon(
                      _useMockBle ? Icons.bug_report : Icons.bluetooth,
                      size: 40,
                      color: _useMockBle ? Colors.orange : Colors.blue,
                    ),
                  ),
                ),
                
                const SizedBox(height: 30),
                
                const Icon(
                  Icons.volume_up,
                  size: 100,
                  color: Colors.blue,
                ),
                
                const SizedBox(height: 20),
                
                const Text(
                  '알람 소리 테스트',
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                
                const SizedBox(height: 30),
                
                // 한 번 재생 버튼
                ElevatedButton.icon(
                  onPressed: () {
                    _viewModel.playAlarmSound();
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('🔊 알람 소리 재생 중...'),
                        duration: Duration(seconds: 2),
                      ),
                    );
                  },
                  icon: const Icon(Icons.play_arrow, size: 28),
                  label: const Text('알람 소리 재생 (1회)'),
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 56),
                    textStyle: const TextStyle(fontSize: 18),
                  ),
                ),
                
                const SizedBox(height: 15),
                
                // 반복 재생 버튼
                ElevatedButton.icon(
                  onPressed: () {
                    _viewModel.playAlarmSoundLoop();
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('🔁 알람 소리 반복 재생 중...'),
                        duration: Duration(seconds: 2),
                        backgroundColor: Colors.orange,
                      ),
                    );
                  },
                  icon: const Icon(Icons.loop, size: 28),
                  label: const Text('알람 소리 반복 재생'),
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 56),
                    backgroundColor: Colors.orange,
                    foregroundColor: Colors.white,
                    textStyle: const TextStyle(fontSize: 18),
                  ),
                ),
                
                const SizedBox(height: 15),
                
                // 정지 버튼
                ElevatedButton.icon(
                  onPressed: () {
                    _viewModel.stopAlarmSound();
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('⏹️ 알람 소리 정지'),
                        duration: Duration(seconds: 1),
                        backgroundColor: Colors.red,
                      ),
                    );
                  },
                  icon: const Icon(Icons.stop, size: 28),
                  label: const Text('알람 소리 정지'),
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 56),
                    backgroundColor: Colors.red,
                    foregroundColor: Colors.white,
                    textStyle: const TextStyle(fontSize: 18),
                  ),
                ),
                
                const SizedBox(height: 30),
                
                const Divider(thickness: 2),
                
                const SizedBox(height: 20),
                
                // BLE 연결 테스트 버튼 (Mock 모드일 때만)
                if (_useMockBle)
                  ElevatedButton.icon(
                    onPressed: () {
                      _viewModel.connectToMockDevice();
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('🔗 Mock BLE 서버에 연결 중... (5초마다 자동 신호 전송)'),
                          duration: Duration(seconds: 3),
                          backgroundColor: Colors.green,
                        ),
                      );
                    },
                    icon: const Icon(Icons.bluetooth_connected, size: 28),
                    label: const Text('Mock BLE 연결 시작'),
                    style: ElevatedButton.styleFrom(
                      minimumSize: const Size(double.infinity, 56),
                      backgroundColor: Colors.green,
                      foregroundColor: Colors.white,
                      textStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                  ),
                
                const SizedBox(height: 20),
                
                // 연결 상태 표시
                Consumer<ActionViewModel>(
                  builder: (context, viewModel, child) {
                    final isConnected = viewModel.connectedDeviceId != null;
                    return Card(
                      elevation: 3,
                      color: isConnected ? Colors.green.shade50 : Colors.grey.shade100,
                      child: Padding(
                        padding: const EdgeInsets.all(20.0),
                        child: Column(
                          children: [
                            Icon(
                              isConnected ? Icons.check_circle : Icons.cancel,
                              size: 48,
                              color: isConnected ? Colors.green : Colors.grey,
                            ),
                            const SizedBox(height: 12),
                            const Text(
                              '연결 상태',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              viewModel.connectedDeviceId ?? '연결된 기기 없음',
                              style: TextStyle(
                                fontSize: 16,
                                color: isConnected ? Colors.green : Colors.grey,
                                fontWeight: FontWeight.w600,
                              ),
                              textAlign: TextAlign.center,
                            ),
                            if (isConnected && _useMockBle) ...[
                              const SizedBox(height: 8),
                              const Text(
                                '⏱️ 5초마다 자동으로 신호 전송 중',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.orange,
                                  fontStyle: FontStyle.italic,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}