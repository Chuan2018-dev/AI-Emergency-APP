import 'package:flutter/material.dart';

class LoginScreen extends StatefulWidget {
  final Future<void> Function(String email, String password, bool registerMode) onSubmit;
  const LoginScreen({super.key, required this.onSubmit});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final email = TextEditingController();
  final password = TextEditingController();
  bool registerMode = false;
  bool loading = false;
  String error = '';

  @override
  void initState() {
    super.initState();
    email.text = 'user@slsu.local';
    password.text = 'password123';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('SLSU Emergency Login')),
      body: Center(
        child: Card(
          child: Container(
            width: 380,
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('Emergency Access Portal', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 10),
                TextField(controller: email, decoration: const InputDecoration(labelText: 'Email')),
                TextField(controller: password, decoration: const InputDecoration(labelText: 'Password'), obscureText: true),
                SwitchListTile(
                  title: const Text('Register new account'),
                  value: registerMode,
                  onChanged: (v) => setState(() => registerMode = v),
                ),
                const SizedBox(height: 6),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
                  onPressed: loading
                      ? null
                      : () async {
                          setState(() {
                            loading = true;
                            error = '';
                          });
                          try {
                            await widget.onSubmit(email.text.trim(), password.text.trim(), registerMode);
                          } catch (e) {
                            setState(() => error = e.toString());
                          } finally {
                            if (mounted) setState(() => loading = false);
                          }
                        },
                  child: Text(loading ? 'Please wait...' : (registerMode ? 'Register' : 'Login')),
                ),
                if (error.isNotEmpty) Text(error, style: const TextStyle(color: Colors.redAccent)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
