import 'dart:math';
import 'dart:typed_data';

class PasswordGeneratorOptions {
  final int length;
  final bool includeUppercase;
  final bool includeLowercase;
  final bool includeNumbers;
  final bool includeSpecial;

  const PasswordGeneratorOptions({
    this.length = 16,
    this.includeUppercase = true,
    this.includeLowercase = true,
    this.includeNumbers = true,
    this.includeSpecial = true,
  });

  PasswordGeneratorOptions copyWith({
    int? length,
    bool? includeUppercase,
    bool? includeLowercase,
    bool? includeNumbers,
    bool? includeSpecial,
  }) {
    return PasswordGeneratorOptions(
      length: length ?? this.length,
      includeUppercase: includeUppercase ?? this.includeUppercase,
      includeLowercase: includeLowercase ?? this.includeLowercase,
      includeNumbers: includeNumbers ?? this.includeNumbers,
      includeSpecial: includeSpecial ?? this.includeSpecial,
    );
  }
}

class PasswordGenerator {
  static const String _uppercaseChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  static const String _lowercaseChars = 'abcdefghijklmnopqrstuvwxyz';
  static const String _numberChars = '0123456789';
  static const String _specialChars = '!@#\$%^&*()_+-=[]{}|;:,.<>?';

  final Random _secureRandom;

  PasswordGenerator() : _secureRandom = Random.secure();

  String generate(PasswordGeneratorOptions options) {
    final charPool = StringBuffer();

    if (options.includeUppercase) charPool.write(_uppercaseChars);
    if (options.includeLowercase) charPool.write(_lowercaseChars);
    if (options.includeNumbers) charPool.write(_numberChars);
    if (options.includeSpecial) charPool.write(_specialChars);

    if (charPool.isEmpty) {
      charPool.write(_lowercaseChars);
    }

    final chars = charPool.toString();
    final passwordChars = <String>[];

    if (options.includeUppercase) {
      passwordChars.add(_getSecureRandomChar(_uppercaseChars));
    }
    if (options.includeLowercase) {
      passwordChars.add(_getSecureRandomChar(_lowercaseChars));
    }
    if (options.includeNumbers) {
      passwordChars.add(_getSecureRandomChar(_numberChars));
    }
    if (options.includeSpecial) {
      passwordChars.add(_getSecureRandomChar(_specialChars));
    }

    final remainingLength = options.length - passwordChars.length;
    for (var i = 0; i < remainingLength; i++) {
      passwordChars.add(_getSecureRandomChar(chars));
    }

    passwordChars.shuffle(_secureRandom);

    return passwordChars.join();
  }

  String _getSecureRandomChar(String chars) {
    final randomIndex = _secureRandom.nextInt(chars.length);
    return chars[randomIndex];
  }

  static int evaluateStrength(String password) {
    if (password.isEmpty) return 0;

    int score = 0;

    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (password.length >= 16) score++;

    if (RegExp(r'[a-z]').hasMatch(password)) score++;
    if (RegExp(r'[A-Z]').hasMatch(password)) score++;
    if (RegExp(r'[0-9]').hasMatch(password)) score++;
    if (RegExp(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]').hasMatch(password)) score++;

    if (RegExp(r'(.)\1{2,}').hasMatch(password)) score -= 1;
    if (RegExp(r'(012|123|234|345|456|567|678|789|890)').hasMatch(password)) score -= 1;
    if (RegExp(r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', caseSensitive: false).hasMatch(password)) score -= 1;

    return score.clamp(0, 4);
  }

  static String getStrengthLabel(int level) {
    switch (level) {
      case 0:
        return '极弱';
      case 1:
        return '弱';
      case 2:
        return '一般';
      case 3:
        return '良好';
      case 4:
        return '强';
      default:
        return '未知';
    }
  }

  static List<String> getStrengthSuggestions(String password) {
    final suggestions = <String>[];

    if (password.length < 12) {
      suggestions.add('增加密码长度到 12 位以上');
    }
    if (!RegExp(r'[A-Z]').hasMatch(password)) {
      suggestions.add('添加大写字母');
    }
    if (!RegExp(r'[a-z]').hasMatch(password)) {
      suggestions.add('添加小写字母');
    }
    if (!RegExp(r'[0-9]').hasMatch(password)) {
      suggestions.add('添加数字');
    }
    if (!RegExp(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]').hasMatch(password)) {
      suggestions.add('添加特殊字符');
    }
    if (RegExp(r'(.)\1{2,}').hasMatch(password)) {
      suggestions.add('避免重复字符');
    }

    return suggestions;
  }
}
