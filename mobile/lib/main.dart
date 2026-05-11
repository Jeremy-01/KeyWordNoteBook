import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'core/security/security_service.dart';

Future<void> _checkSecurity() async {
  final securityService = SecurityService.instance;
  final isCompromised = await securityService.checkDeviceSecurity();
  if (isCompromised) {
    debugPrint('Security warning: Device is compromised');
  }
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await _checkSecurity();

  runApp(
    const ProviderScope(
      child: KeyBookApp(),
    ),
  );
}
