import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'services/api_service.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  final api = ApiService();
  String? token;

  @override
  void initState() {
    super.initState();
    _loadToken();
  }

  Future<void> _loadToken() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() => token = prefs.getString('token'));
  }

  Future<void> _auth(String email, String password, bool registerMode) async {
    final res = registerMode ? await api.register(email, password) : await api.login(email, password);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('token', res['token']);
    setState(() => token = res['token']);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'SLSU Emergency MVP',
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF061833),
        colorScheme: const ColorScheme.dark(primary: Colors.redAccent),
        appBarTheme: const AppBarTheme(backgroundColor: Color(0xFF0A2348)),
        cardTheme: const CardTheme(color: Color(0xFF10264A)),
      ),
      home: token == null ? LoginScreen(onSubmit: _auth) : HomeScreen(token: token!, api: api),
    );
  }
}
