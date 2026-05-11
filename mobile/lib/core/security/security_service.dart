import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'screenshot_protection.dart';

class JailbreakDetection {
  static Future<bool> isDeviceCompromised() async {
    if (Platform.isAndroid) {
      return await _checkAndroidRoot();
    } else if (Platform.isIOS) {
      return await _checkIOSJailbreak();
    }
    return false;
  }

  static Future<bool> _checkAndroidRoot() async {
    final rootPaths = [
      '/system/app/Superuser.apk',
      '/sbin/su',
      '/system/bin/su',
      '/system/xbin/su',
      '/data/local/xbin/su',
      '/data/local/bin/su',
      '/system/sd/xbin/su',
      '/system/bin/failsafe/su',
      '/data/local/su',
      '/su/bin/su',
    ];

    for (final path in rootPaths) {
      if (await File(path).exists()) {
        return true;
      }
    }

    try {
      final result = await Process.run('which', ['su']);
      if (result.exitCode == 0) {
        return true;
      }
    } catch (_) {}

    return false;
  }

  static Future<bool> _checkIOSJailbreak() async {
    final jailbreakPaths = [
      '/Applications/Cydia.app',
      '/Library/MobileSubstrate/MobileSubstrate.dylib',
      '/bin/bash',
      '/usr/sbin/sshd',
      '/etc/apt',
      '/private/var/lib/apt/',
      '/usr/bin/ssh',
      '/private/var/stash',
      '/private/var/lib/cydia',
      '/private/var/tmp/cydia.log',
      '/System/Library/LaunchDaemons/com.ikey.bbot.plist',
      '/System/Library/LaunchDaemons/com.saurik.Cydia.Startup.plist',
      '/Library/MobileSubstrate/DynamicLibraries/LiveClock.plist',
      '/Library/MobileSubstrate/DynamicLibraries/Veency.plist',
    ];

    for (final path in jailbreakPaths) {
      if (await File(path).exists()) {
        return true;
      }
    }

    try {
      final cydia = await File('/Applications/Cydia.app').open();
      await cydia.close();
      return true;
    } catch (_) {}

    return false;
  }

  static String getSecurityWarningMessage() {
    if (Platform.isAndroid) {
      return '检测到设备已 Root，应用数据可能面临安全风险。';
    } else if (Platform.isIOS) {
      return '检测到设备已越狱，应用数据可能面临安全风险。';
    }
    return '检测到设备存在安全风险，应用数据可能面临风险。';
  }
}

class SecurityService {
  static SecurityService? _instance;
  static SecurityService get instance => _instance ??= SecurityService._();

  SecurityService._();

  bool _isInitialized = false;
  bool _isLocked = false;
  VoidCallback? _onLockCallback;
  Timer? _idleTimer;
  Duration _lockDuration = const Duration(minutes: 1);
  DateTime? _lastActivity;

  bool get isLocked => _isLocked;
  bool get isInitialized => _isInitialized;
  Duration get lockDuration => _lockDuration;

  Future<void> initialize({
    Duration lockDuration = const Duration(minutes: 1),
    VoidCallback? onLock,
  }) async {
    if (_isInitialized) return;

    _lockDuration = lockDuration;
    _onLockCallback = onLock;
    _isInitialized = true;

    final isCompromised = await JailbreakDetection.isDeviceCompromised();
    if (isCompromised) {
      return;
    }

    try {
      await ScreenshotProtection.enable();
    } catch (_) {}
  }

  void setLockDuration(Duration duration) {
    _lockDuration = duration;
    _resetTimer();
  }

  void setOnLock(VoidCallback callback) {
    _onLockCallback = callback;
  }

  void start() {
    _lastActivity = DateTime.now();
    _resetTimer();
  }

  void stop() {
    _idleTimer?.cancel();
    _idleTimer = null;
  }

  void resetTimer() {
    _lastActivity = DateTime.now();
    _resetTimer();
  }

  void _resetTimer() {
    _idleTimer?.cancel();
    if (!_isLocked) {
      _idleTimer = Timer(_lockDuration, _triggerLock);
    }
  }

  void _triggerLock() {
    if (!_isLocked) {
      _isLocked = true;
      _onLockCallback?.call();
    }
  }

  void unlock() {
    _isLocked = false;
    _lastActivity = DateTime.now();
    _resetTimer();
  }

  Duration get timeUntilLock {
    if (_lastActivity == null) return _lockDuration;
    final elapsed = DateTime.now().difference(_lastActivity!);
    final remaining = _lockDuration - elapsed;
    return remaining.isNegative ? Duration.zero : remaining;
  }

  Future<bool> checkDeviceSecurity() async {
    return await JailbreakDetection.isDeviceCompromised();
  }

  String getSecurityWarningMessage() {
    return JailbreakDetection.getSecurityWarningMessage();
  }

  void dispose() {
    stop();
    _isInitialized = false;
  }
}

Future<bool?> showSecurityWarningDialog(
  BuildContext context, {
  required String message,
  VoidCallback? onContinue,
  VoidCallback? onExit,
}) {
  return showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (context) => AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.warning_amber, color: Colors.orange),
          SizedBox(width: 8),
          Text('安全警告'),
        ],
      ),
      content: Text(message),
      actions: [
        TextButton(
          onPressed: () {
            Navigator.of(context).pop(false);
            onExit?.call();
          },
          child: const Text('退出'),
        ),
        ElevatedButton(
          onPressed: () {
            Navigator.of(context).pop(true);
            onContinue?.call();
          },
          child: const Text('继续使用'),
        ),
      ],
    ),
  );
}
