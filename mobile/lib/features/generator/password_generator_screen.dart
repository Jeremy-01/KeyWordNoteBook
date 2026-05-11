import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/generator/password_generator.dart';
import '../../core/utils/clipboard_utils.dart';

class PasswordGeneratorScreen extends StatefulWidget {
  final Function(String)? onPasswordGenerated;

  const PasswordGeneratorScreen({
    super.key,
    this.onPasswordGenerated,
  });

  @override
  State<PasswordGeneratorScreen> createState() => _PasswordGeneratorScreenState();
}

class _PasswordGeneratorScreenState extends State<PasswordGeneratorScreen> {
  final _generator = PasswordGenerator();
  late PasswordGeneratorOptions _options;
  String _generatedPassword = '';

  @override
  void initState() {
    super.initState();
    _options = const PasswordGeneratorOptions();
    _generatePassword();
  }

  void _generatePassword() {
    setState(() {
      _generatedPassword = _generator.generate(_options);
    });
  }

  void _copyToClipboard() {
    ClipboardUtils.copyWithAutoClear(
      context,
      _generatedPassword,
      label: '密码',
    );
  }

  void _applyPassword() {
    if (widget.onPasswordGenerated != null) {
      widget.onPasswordGenerated!(_generatedPassword);
    }
    Navigator.of(context).pop(_generatedPassword);
  }

  @override
  Widget build(BuildContext context) {
    final strength = PasswordGenerator.evaluateStrength(_generatedPassword);
    final strengthColor = _getStrengthColor(strength);
    final strengthLabel = PasswordGenerator.getStrengthLabel(strength);

    return Scaffold(
      appBar: AppBar(
        title: const Text('密码生成器'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: SelectableText(
                        _generatedPassword,
                        style: const TextStyle(
                          fontSize: 18,
                          fontFamily: 'monospace',
                          fontWeight: FontWeight.w600,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: strength / 4,
                              backgroundColor: Colors.grey.shade200,
                              valueColor: AlwaysStoppedAnimation<Color>(strengthColor),
                              minHeight: 6,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Text(
                          strengthLabel,
                          style: TextStyle(
                            color: strengthColor,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _copyToClipboard,
                    icon: const Icon(Icons.copy),
                    label: const Text('复制'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _generatePassword,
                    icon: const Icon(Icons.refresh),
                    label: const Text('重新生成'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '密码长度: ${_options.length}',
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 16,
                      ),
                    ),
                    Slider(
                      value: _options.length.toDouble(),
                      min: 8,
                      max: 64,
                      divisions: 56,
                      label: _options.length.toString(),
                      onChanged: (value) {
                        setState(() {
                          _options = _options.copyWith(length: value.round());
                        });
                        _generatePassword();
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '字符类型',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 8),
                    CheckboxListTile(
                      title: const Text('大写字母 (A-Z)'),
                      value: _options.includeUppercase,
                      onChanged: (value) {
                        setState(() {
                          _options = _options.copyWith(includeUppercase: value ?? true);
                        });
                        _generatePassword();
                      },
                      dense: true,
                    ),
                    CheckboxListTile(
                      title: const Text('小写字母 (a-z)'),
                      value: _options.includeLowercase,
                      onChanged: (value) {
                        setState(() {
                          _options = _options.copyWith(includeLowercase: value ?? true);
                        });
                        _generatePassword();
                      },
                      dense: true,
                    ),
                    CheckboxListTile(
                      title: const Text('数字 (0-9)'),
                      value: _options.includeNumbers,
                      onChanged: (value) {
                        setState(() {
                          _options = _options.copyWith(includeNumbers: value ?? true);
                        });
                        _generatePassword();
                      },
                      dense: true,
                    ),
                    CheckboxListTile(
                      title: const Text('特殊字符 (!@#\$%...)'),
                      value: _options.includeSpecial,
                      onChanged: (value) {
                        setState(() {
                          _options = _options.copyWith(includeSpecial: value ?? true);
                        });
                        _generatePassword();
                      },
                      dense: true,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            if (widget.onPasswordGenerated != null)
              ElevatedButton(
                onPressed: _applyPassword,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: const Text('使用此密码'),
              ),
          ],
        ),
      ),
    );
  }

  Color _getStrengthColor(int level) {
    switch (level) {
      case 0:
        return Colors.red;
      case 1:
        return Colors.orange;
      case 2:
        return Colors.yellow.shade700;
      case 3:
        return Colors.lightGreen;
      case 4:
        return Colors.green;
      default:
        return Colors.grey;
    }
  }
}

Future<String?> showPasswordGeneratorDialog(
  BuildContext context, {
  Function(String)? onPasswordGenerated,
}) {
  return showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => DraggableScrollableSheet(
      initialChildSize: 0.7,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      builder: (context, scrollController) => Container(
        decoration: BoxDecoration(
          color: Theme.of(context).scaffoldBackgroundColor,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: PasswordGeneratorScreen(
          onPasswordGenerated: onPasswordGenerated,
        ),
      ),
    ),
  );
}
