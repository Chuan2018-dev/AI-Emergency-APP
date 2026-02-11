import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

class LocalQueue {
  static const _key = 'offline_reports_queue';

  Future<List<Map<String, dynamic>>> readQueue() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null) return [];
    final decoded = jsonDecode(raw) as List;
    return decoded.map((e) => Map<String, dynamic>.from(e)).toList();
  }

  Future<void> add(Map<String, dynamic> item) async {
    final prefs = await SharedPreferences.getInstance();
    final list = await readQueue();
    list.add(item);
    await prefs.setString(_key, jsonEncode(list));
  }

  Future<void> setQueue(List<Map<String, dynamic>> list) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(list));
  }
}
