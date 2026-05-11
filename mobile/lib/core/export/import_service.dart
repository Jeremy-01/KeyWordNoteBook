import 'dart:convert';
import 'package:csv/csv.dart';
import '../crypto/crypto_service.dart';
import '../../data/models/key_item_model.dart';

class ImportResult {
  final int totalCount;
  final int successCount;
  final int failedCount;
  final List<String> errors;

  ImportResult({
    required this.totalCount,
    required this.successCount,
    required this.failedCount,
    this.errors = const [],
  });
}

class ImportService {
  final CryptoService _cryptoService;

  ImportService({CryptoService? cryptoService})
      : _cryptoService = cryptoService ?? CryptoService();

  Future<List<KeyItemModel>> parseCsv(String csvContent) async {
    final List<List<dynamic>> rows =
        const CsvToListConverter().convert(csvContent);

    if (rows.isEmpty) return [];

    final headers = rows.first.map((e) => e.toString().toLowerCase()).toList();
    final items = <KeyItemModel>[];

    for (var i = 1; i < rows.length; i++) {
      final row = rows[i];
      if (row.length < 3) continue;

      try {
        final item = _parseRowToItem(headers, row);
        items.add(item);
      } catch (e) {
        continue;
      }
    }

    return items;
  }

  KeyItemModel _parseRowToItem(List<String> headers, List<dynamic> row) {
    String getValue(String header) {
      final headerIndex = headers.indexOf(header.toLowerCase());
      if (headerIndex != -1 && headerIndex < row.length) {
        return row[headerIndex]?.toString() ?? '';
      }
      return '';
    }

    int getIntValue(String header, {int defaultValue = 0}) {
      final value = getValue(header);
      return int.tryParse(value) ?? defaultValue;
    }

    bool getBoolValue(String header) {
      final value = getValue(header).toLowerCase();
      return value == 'true' || value == '1';
    }

    return KeyItemModel(
      index: '',
      url: getValue('url'),
      username: getValue('username'),
      password: getValue('password').isEmpty ? null : getValue('password'),
      passwordLevel: getIntValue('passwordlevel'),
      linkUrl: getValue('linkurl'),
      note: getValue('note'),
      isFavorite: getBoolValue('isfavorite'),
      groupId: getValue('groupid').isEmpty ? null : getValue('groupid'),
    );
  }

  Future<List<KeyItemModel>> parseEncryptedJson(
    String jsonContent,
    String masterPassword,
  ) async {
    final Map<String, dynamic> wrapper = jsonDecode(jsonContent);

    if (wrapper['format'] != 'encrypted_keybook_backup') {
      throw Exception('无效的加密备份格式');
    }

    final encryptedData = wrapper['data'] as String;
    final decrypted = await _cryptoService.decryptString(encryptedData, masterPassword);
    final Map<String, dynamic> data = jsonDecode(decrypted);

    final itemsJson = data['items'] as List<dynamic>;
    return itemsJson.map((json) => KeyItemModel.fromJson(json)).toList();
  }

  Future<List<KeyItemModel>> parsePlainJson(String jsonContent) async {
    final Map<String, dynamic> data = jsonDecode(jsonContent);
    final itemsJson = data['items'] as List<dynamic>;
    return itemsJson.map((json) => KeyItemModel.fromJson(json)).toList();
  }

  ImportResult validateItems(List<KeyItemModel> items) {
    int successCount = 0;
    int failedCount = 0;
    final errors = <String>[];

    for (var i = 0; i < items.length; i++) {
      final item = items[i];
      if (item.url.isEmpty && item.username.isEmpty) {
        failedCount++;
        errors.add('第 ${i + 1} 行：URL 和用户名不能同时为空');
      } else {
        successCount++;
      }
    }

    return ImportResult(
      totalCount: items.length,
      successCount: successCount,
      failedCount: failedCount,
      errors: errors,
    );
  }
}
