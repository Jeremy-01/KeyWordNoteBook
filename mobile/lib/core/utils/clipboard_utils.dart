import 'dart:async';
import 'package:flutter/services.dart';
import 'package:flutter/material.dart';

class ClipboardUtils {
  static Timer? _clearTimer;
  static String? _lastCopiedText;
  static const Duration clearDelay = Duration(seconds: 15);

  static Future<void> copyWithAutoClear(
    BuildContext context,
    String text, {
    String label = '内容',
    Duration? delay,
    VoidCallback? onCleared,
  }) async {
    await Clipboard.setData(ClipboardData(text: text));
    _lastCopiedText = text;

    _clearTimer?.cancel();

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$label 已复制，${(delay ?? clearDelay).inSeconds}秒后自动清除'),
        duration: Duration(seconds: ((delay ?? clearDelay).inSeconds).clamp(1, 10)),
        action: SnackBarAction(
          label: '清除',
          onPressed: () {
            cancelTimer();
          },
        ),
      ),
    );

    _clearTimer = Timer(delay ?? clearDelay, () async {
      final currentContent = await Clipboard.getData(Clipboard.kTextPlain);
      if (currentContent?.text == _lastCopiedText) {
        await clearClipboard();
        onCleared?.call();
      }
      _lastCopiedText = null;
    });
  }

  static Future<void> clearClipboard() async {
    await Clipboard.setData(const ClipboardData(text: ''));
    _lastCopiedText = null;
  }

  static void cancelTimer() {
    _clearTimer?.cancel();
    _clearTimer = null;
    _lastCopiedText = null;
  }

  static bool get hasPendingClear => _clearTimer?.isActive ?? false;
}
