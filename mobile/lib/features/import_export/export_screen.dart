import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';

import '../../core/export/export_service.dart';
import '../../data/providers/keybook_provider.dart';

final exportServiceProvider = Provider<ExportService>((ref) {
  return ExportService();
});

class ExportScreen extends ConsumerStatefulWidget {
  const ExportScreen({super.key});

  @override
  ConsumerState<ExportScreen> createState() => _ExportScreenState();
}

class _ExportScreenState extends ConsumerState<ExportScreen> {
  ExportFormat _selectedFormat = ExportFormat.csv;
  bool _isExporting = false;
  String? _tempFilePath;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('导出数据'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '选择导出格式',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 16),
                    RadioListTile<ExportFormat>(
                      title: const Text('CSV 格式'),
                      subtitle: const Text('通用格式，可导入到其他密码管理工具'),
                      value: ExportFormat.csv,
                      groupValue: _selectedFormat,
                      onChanged: (value) {
                        setState(() => _selectedFormat = value!);
                      },
                    ),
                    RadioListTile<ExportFormat>(
                      title: const Text('加密备份'),
                      subtitle: const Text('加密格式，需输入主密码解密'),
                      value: ExportFormat.encryptedJson,
                      groupValue: _selectedFormat,
                      onChanged: (value) {
                        setState(() => _selectedFormat = value!);
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
                      '导出说明',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      '• 导出的数据包含所有密码条目\n'
                      '• 加密备份使用您的主密码加密\n'
                      '• 导出的文件仅在分享期间临时存储',
                      style: TextStyle(color: Colors.grey),
                    ),
                  ],
                ),
              ),
            ),
            const Spacer(),
            ElevatedButton(
              onPressed: _isExporting ? null : _handleExport,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              child: _isExporting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('导出'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleExport() async {
    setState(() => _isExporting = true);

    try {
      final keyBookState = ref.read(keyBookProvider);
      final items = keyBookState.items;

      if (items.isEmpty) {
        _showError('没有可导出的数据');
        return;
      }

      String content;
      String fileName;

      if (_selectedFormat == ExportFormat.csv) {
        final exportService = ref.read(exportServiceProvider);
        content = await exportService.exportToCsv(items);
        fileName = 'passwords_${DateTime.now().millisecondsSinceEpoch}.csv';
      } else {
        final masterPassword = await _showPasswordDialog();
        if (masterPassword == null || masterPassword.isEmpty) {
          _showError('请输入主密码');
          return;
        }
        final exportService = ref.read(exportServiceProvider);
        content = await exportService.exportToEncryptedJson(items, masterPassword);
        fileName = 'encrypted_backup_${DateTime.now().millisecondsSinceEpoch}.json';
      }

      final directory = await getTemporaryDirectory();
      final file = File('${directory.path}/$fileName');
      _tempFilePath = file.path;
      await file.writeAsString(content);

      await Share.shareXFiles(
        [XFile(file.path)],
        subject: '密码本导出',
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('导出成功')),
        );
      }
    } catch (e) {
      _showError('导出失败: $e');
    } finally {
      if (mounted) {
        setState(() => _isExporting = false);
      }
      _cleanupTempFile();
    }
  }

  Future<void> _cleanupTempFile() async {
    if (_tempFilePath != null) {
      try {
        final file = File(_tempFilePath!);
        if (await file.exists()) {
          await file.delete();
        }
      } catch (_) {}
      _tempFilePath = null;
    }
  }

  Future<String?> _showPasswordDialog() async {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('输入主密码'),
        content: TextField(
          controller: controller,
          obscureText: true,
          decoration: const InputDecoration(
            labelText: '主密码',
            hintText: '请输入用于加密的主密码',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(controller.text),
            child: const Text('确认'),
          ),
        ],
      ),
    );
  }

  void _showError(String message) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
}
