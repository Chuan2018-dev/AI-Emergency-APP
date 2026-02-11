import 'dart:convert';
import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:latlong2/latlong.dart';

import '../models/report_item.dart';
import '../services/api_service.dart';
import '../services/local_queue.dart';

class HomeScreen extends StatefulWidget {
  final String token;
  final ApiService api;
  const HomeScreen({super.key, required this.token, required this.api});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final description = TextEditingController();
  final latitude = TextEditingController();
  final longitude = TextEditingController();
  final localQueue = LocalQueue();
  final picker = ImagePicker();

  String emergencyType = 'Accident';
  bool offline = false;
  bool loading = false;
  File? selfie;
  File? accident;
  List<ReportItem> myReports = [];
  String info = '';
  LatLng markerPoint = const LatLng(14.1207, 121.1548);

  @override
  void initState() {
    super.initState();
    _initGps();
    loadMyReports();
  }

  Future<void> _initGps() async {
    final enabled = await Geolocator.isLocationServiceEnabled();
    if (!enabled) return;
    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) perm = await Geolocator.requestPermission();
    if (perm == LocationPermission.deniedForever || perm == LocationPermission.denied) return;
    final pos = await Geolocator.getCurrentPosition();
    setState(() {
      markerPoint = LatLng(pos.latitude, pos.longitude);
      latitude.text = pos.latitude.toStringAsFixed(6);
      longitude.text = pos.longitude.toStringAsFixed(6);
    });
  }

  Future<void> pickImage(bool isSelfie) async {
    final file = await picker.pickImage(source: ImageSource.camera, imageQuality: 75);
    if (file == null) return;
    setState(() {
      if (isSelfie) {
        selfie = File(file.path);
      } else {
        accident = File(file.path);
      }
    });
  }

  Future<void> loadMyReports() async {
    final data = await widget.api.myReports(widget.token);
    setState(() => myReports = data.map((e) => ReportItem.fromJson(e)).toList());
  }

  String buildLoraPayload() {
    final payload = {
      'device_id': 'android-emulator-01',
      'timestamp': DateTime.now().toIso8601String(),
      'lat': latitude.text,
      'lng': longitude.text,
      'emergency_type': emergencyType,
    };
    final hash = base64Url.encode(utf8.encode(jsonEncode(payload))).substring(0, 16);
    payload['hash'] = hash;
    return jsonEncode(payload);
  }

  Color severityColor(String label) {
    switch (label.toLowerCase()) {
      case 'critical':
        return Colors.redAccent;
      case 'medium':
        return Colors.orange;
      default:
        return Colors.green;
    }
  }

  Future<bool> confirmSubmit() async {
    return await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: const Color(0xFF10264A),
            title: const Text('Confirm Submission'),
            content: const Text('Are you sure you want to send this emergency report?'),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
              ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Submit')),
            ],
          ),
        ) ??
        false;
  }

  Future<void> submit() async {
    if (selfie == null || accident == null) {
      setState(() => info = 'Selfie and accident photo are required.');
      return;
    }
    if (!await confirmSubmit()) return;

    final payload = {
      'emergency_type': emergencyType,
      'description': description.text,
      'latitude': latitude.text,
      'longitude': longitude.text,
      'selfie_path': selfie!.path,
      'accident_path': accident!.path,
      'device_id': 'android-emulator-01',
      'lora_payload': buildLoraPayload(),
    };

    final conn = await Connectivity().checkConnectivity();
    final online = conn != ConnectivityResult.none;

    setState(() => loading = true);
    try {
      if (offline || !online) {
        await localQueue.add(payload);
        setState(() => info = 'Offline mode active. Queued + LoRa payload:\n${payload['lora_payload']}');
        return;
      }

      await widget.api.submitReport(
        token: widget.token,
        emergencyType: emergencyType,
        description: description.text,
        latitude: double.tryParse(latitude.text) ?? 0,
        longitude: double.tryParse(longitude.text) ?? 0,
        selfie: selfie!,
        accident: accident!,
        deviceId: 'android-emulator-01',
        loraPayload: payload['lora_payload']!,
      );
      await syncQueued();
      await loadMyReports();
      setState(() => info = 'Report submitted successfully.');
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> syncQueued() async {
    final queued = await localQueue.readQueue();
    if (queued.isEmpty) return;
    final remaining = <Map<String, dynamic>>[];
    for (final item in queued) {
      try {
        await widget.api.submitReport(
          token: widget.token,
          emergencyType: item['emergency_type'],
          description: item['description'],
          latitude: double.parse(item['latitude']),
          longitude: double.parse(item['longitude']),
          selfie: File(item['selfie_path']),
          accident: File(item['accident_path']),
          deviceId: item['device_id'],
          loraPayload: item['lora_payload'],
        );
      } catch (_) {
        remaining.add(item);
      }
    }
    await localQueue.setQueue(remaining);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF061833),
      appBar: AppBar(
        title: const Text('SLSU Emergency Reporter'),
        backgroundColor: const Color(0xFF0A2348),
      ),
      body: Stack(
        children: [
          SingleChildScrollView(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Card(
                  color: const Color(0xFF10264A),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      children: [
                        DropdownButtonFormField<String>(
                          value: emergencyType,
                          dropdownColor: const Color(0xFF10264A),
                          items: ['Accident', 'Medical', 'Fire', 'Crime', 'Other']
                              .map((e) => DropdownMenuItem(value: e, child: Text(e)))
                              .toList(),
                          onChanged: (v) => setState(() => emergencyType = v!),
                          decoration: const InputDecoration(labelText: 'Emergency Type'),
                        ),
                        TextField(controller: description, decoration: const InputDecoration(labelText: 'Description')),
                        Row(
                          children: [
                            Expanded(child: TextField(controller: latitude, decoration: const InputDecoration(labelText: 'Latitude'))),
                            const SizedBox(width: 8),
                            Expanded(child: TextField(controller: longitude, decoration: const InputDecoration(labelText: 'Longitude'))),
                          ],
                        ),
                        const SizedBox(height: 10),
                        SizedBox(
                          height: 180,
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(10),
                            child: FlutterMap(
                              options: MapOptions(
                                initialCenter: markerPoint,
                                initialZoom: 15,
                                onTap: (tapPosition, latLng) {
                                  setState(() {
                                    markerPoint = latLng;
                                    latitude.text = latLng.latitude.toStringAsFixed(6);
                                    longitude.text = latLng.longitude.toStringAsFixed(6);
                                  });
                                },
                              ),
                              children: [
                                TileLayer(urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'),
                                MarkerLayer(markers: [
                                  Marker(
                                    point: markerPoint,
                                    width: 42,
                                    height: 42,
                                    child: const Icon(Icons.location_on, color: Colors.redAccent, size: 40),
                                  )
                                ])
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 6),
                        const Text('Map preview: tap to adjust marker location before submit.'),
                        SwitchListTile(
                          title: const Text('No Internet? (simulate LoRa fallback)'),
                          value: offline,
                          onChanged: (v) => setState(() => offline = v),
                        ),
                        Row(children: [
                          ElevatedButton(onPressed: () => pickImage(true), child: const Text('Capture Selfie')),
                          const SizedBox(width: 12),
                          if (selfie != null) const Icon(Icons.check_circle, color: Colors.greenAccent),
                        ]),
                        Row(children: [
                          ElevatedButton(onPressed: () => pickImage(false), child: const Text('Capture Accident Photo')),
                          const SizedBox(width: 12),
                          if (accident != null) const Icon(Icons.check_circle, color: Colors.greenAccent),
                        ]),
                        const SizedBox(height: 8),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
                          onPressed: loading ? null : submit,
                          child: const Text('Submit Emergency Report'),
                        ),
                        const SizedBox(height: 8),
                        OutlinedButton(
                          onPressed: () async {
                            await syncQueued();
                            await loadMyReports();
                          },
                          child: const Text('Sync Offline Queue'),
                        ),
                        if (info.isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: 8.0),
                            child: Text(info, style: const TextStyle(color: Colors.orangeAccent)),
                          ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                const Text('My Reports', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                ...myReports.map((r) {
                  return Card(
                    color: const Color(0xFF0D2245),
                    child: Padding(
                      padding: const EdgeInsets.all(10),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text('${r.emergencyType} • ${r.status}', style: const TextStyle(fontWeight: FontWeight.bold)),
                              const Spacer(),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: severityColor(r.severityLabel).withOpacity(0.2),
                                  borderRadius: BorderRadius.circular(20),
                                  border: Border.all(color: severityColor(r.severityLabel)),
                                ),
                                child: Text(r.severityLabel, style: TextStyle(color: severityColor(r.severityLabel))),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(r.description),
                          const SizedBox(height: 8),
                          LinearProgressIndicator(
                            value: (r.verificationScore / 100).clamp(0, 1),
                            minHeight: 8,
                            color: r.verificationScore >= 70
                                ? Colors.green
                                : (r.verificationScore >= 40 ? Colors.orange : Colors.redAccent),
                            backgroundColor: Colors.white12,
                          ),
                          const SizedBox(height: 4),
                          Text('Verification Score: ${r.verificationScore.toStringAsFixed(1)}'),
                        ],
                      ),
                    ),
                  );
                }),
              ],
            ),
          ),
          if (loading)
            Container(
              color: Colors.black45,
              child: const Center(child: CircularProgressIndicator(color: Colors.redAccent)),
            ),
        ],
      ),
    );
  }
}
