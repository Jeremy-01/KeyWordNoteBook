import 'dart:io';
import 'package:flutter/services.dart';

class ScreenshotProtection {
  static bool _isEnabled = false;
  static const _channel = MethodChannel('com.keywordnotebook/security');

  static bool get isEnabled => _isEnabled;

  static Future<void> enable() async {
    if (Platform.isAndroid) {
      await _enableAndroidProtection();
    } else if (Platform.isIOS) {
      await _enableIOSProtection();
    }
    _isEnabled = true;
  }

  static Future<void> disable() async {
    if (Platform.isAndroid) {
      await _disableAndroidProtection();
    } else if (Platform.isIOS) {
      await _disableIOSProtection();
    }
    _isEnabled = false;
  }

  static Future<void> _enableAndroidProtection() async {
    try {
      await _channel.invokeMethod('enableScreenshotProtection');
    } on PlatformException catch (_) {
      // Platform channel not implemented, screenshot protection requires native code
      // For production, implement FLAG_SECURE in MainActivity.kt
    } on MissingPluginException catch (_) {
      // Plugin not registered, screenshot protection unavailable
    }
  }

  static Future<void> _disableAndroidProtection() async {
    try {
      await _channel.invokeMethod('disableScreenshotProtection');
    } on PlatformException catch (_) {
      // Ignore
    } on MissingPluginException catch (_) {
      // Ignore
    }
  }

  static Future<void> _enableIOSProtection() async {
    try {
      await _channel.invokeMethod('enableScreenshotProtection');
    } on PlatformException catch (_) {
      // For iOS, implement via secure text field or native handler
    } on MissingPluginException catch (_) {
      // Ignore
    }
  }

  static Future<void> _disableIOSProtection() async {
    try {
      await _channel.invokeMethod('disableScreenshotProtection');
    } on PlatformException catch (_) {
      // Ignore
    } on MissingPluginException catch (_) {
      // Ignore
    }
  }
}
