import 'dart:io';

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
