import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

class ApiService {
  final String baseUrl;
  ApiService({this.baseUrl = 'http://10.0.2.2:8000'});

  Future<Map<String, dynamic>> login(String email, String password) async {
    final req = http.MultipartRequest('POST', Uri.parse('$baseUrl/auth/login'));
    req.fields['email'] = email;
    req.fields['password'] = password;
    final res = await req.send();
    final body = await res.stream.bytesToString();
    final jsonBody = jsonDecode(body);
    if (res.statusCode >= 400) throw Exception(jsonBody['detail'] ?? 'Login failed');
    return jsonBody;
  }

  Future<Map<String, dynamic>> register(String email, String password) async {
    final req = http.MultipartRequest('POST', Uri.parse('$baseUrl/auth/register'));
    req.fields['email'] = email;
    req.fields['password'] = password;
    final res = await req.send();
    final body = await res.stream.bytesToString();
    final jsonBody = jsonDecode(body);
    if (res.statusCode >= 400) throw Exception(jsonBody['detail'] ?? 'Register failed');
    return jsonBody;
  }

  Future<Map<String, dynamic>> submitReport({
    required String token,
    required String emergencyType,
    required String description,
    required double latitude,
    required double longitude,
    required File selfie,
    required File accident,
    required String deviceId,
    String loraPayload = '',
  }) async {
    final req = http.MultipartRequest('POST', Uri.parse('$baseUrl/reports'));
    req.headers['Authorization'] = 'Bearer $token';
    req.fields['emergency_type'] = emergencyType;
    req.fields['description'] = description;
    req.fields['latitude'] = latitude.toString();
    req.fields['longitude'] = longitude.toString();
    req.fields['device_id'] = deviceId;
    req.fields['lora_payload'] = loraPayload;
    req.files.add(await http.MultipartFile.fromPath('selfie', selfie.path));
    req.files.add(await http.MultipartFile.fromPath('accident_photo', accident.path));

    final res = await req.send();
    final body = await res.stream.bytesToString();
    final jsonBody = jsonDecode(body);
    if (res.statusCode >= 400) throw Exception(jsonBody['detail'] ?? 'Submit failed');
    return jsonBody;
  }

  Future<List<dynamic>> myReports(String token) async {
    final res = await http.get(Uri.parse('$baseUrl/reports/me'), headers: {'Authorization': 'Bearer $token'});
    final data = jsonDecode(res.body);
    if (res.statusCode >= 400) throw Exception(data['detail'] ?? 'Failed loading reports');
    return data;
  }
}
