# 移动端继续开发规格说明

## Why

当前 KeyWordNoteBook 移动端已完成基础功能开发（认证、密码 CRUD、设置），但在功能性、用户体验和代码质量方面仍存在不足，需要继续完善以达到生产就绪状态。

## What Changes

### 核心功能完善

- **密码生成器**：集成安全的随机密码生成功能，支持自定义长度和字符集
- **导入/导出功能**：支持从 CSV 文件导入密码，支持加密导出备份
- **分组管理**：支持创建文件夹/分组来组织密码条目
- **收藏夹**：支持将常用密码标记为收藏
- **自动填充**：集成系统级自动填充服务（Android Autofill / iOS Keychain）

### 用户体验优化

- **密码可见性默认关闭**：安全增强
- **复制后自动清除剪贴板**：15 秒后自动清除复制的密码
- **快速操作优化**：长按条目弹出操作菜单
- **搜索增强**：支持按网站、用户名、备注搜索
- **排序选项**：按名称、创建时间、最后使用时间排序

### 安全加固

- **会话超时锁定**：无操作自动锁定（时间可配置）
- **Root/越狱检测**：在已 Root/越狱设备上显示安全警告
- **截图防护**：禁止在敏感页面截图
- **密钥轮换**：支持主密码修改后的密钥重新派生
- **生物识别集成**：完成生物识别解锁功能

### 同步功能完善

- **冲突解决策略**：用户选择保留本地/服务器版本
- **同步历史记录**：记录最近 30 天的同步操作
- **离线队列**：离线时操作的自动排队同步
- **Wi-Fi 同步开关**：支持仅在 Wi-Fi 下同步

### 错误处理和边界情况

- **网络错误重试**：指数退避重试机制
- **数据验证**：客户端和服务端双重验证
- **加密失败处理**：优雅降级和错误提示
- **数据库迁移**：支持版本升级时的数据迁移

## Impact

### 受影响的现有功能

| 模块 | 影响 |
|------|------|
| 密码管理 | 新增密码生成、分组、收藏功能 |
| 认证 | 新增生物识别解锁、密钥轮换 |
| 设置 | 新增更多安全设置选项 |
| 同步 | 完善冲突解决和离线支持 |
| UI/UX | 优化交互流程和安全提示 |

### 关键文件/系统

- `lib/data/providers/keybook_provider.dart` - 密码本状态管理
- `lib/data/providers/auth_provider.dart` - 认证状态管理
- `lib/core/crypto/crypto_service.dart` - 加密服务
- `lib/core/sync/sync_service.dart` - 同步服务
- `lib/features/home/home_screen.dart` - 主页 UI
- `lib/features/item/` - 密码条目相关页面

---

## ADDED Requirements

### Requirement: 密码生成器

系统应提供安全的随机密码生成功能。

#### Scenario: 生成符合条件的新密码
- **WHEN** 用户点击密码输入框旁的"生成"按钮
- **THEN** 显示密码生成器弹窗
- **AND** 用户可设置密码长度（8-64 字符）
- **AND** 用户可选择字符类型（大写、小写、数字、特殊字符）
- **AND** 点击"生成"后自动填充到密码输入框

#### Scenario: 复制生成的密码
- **WHEN** 用户点击密码生成器中的"复制"按钮
- **THEN** 密码被复制到剪贴板
- **AND** 显示提示"密码已复制，15秒后自动清除"

### Requirement: 密码分组管理

系统应支持通过文件夹/分组组织密码条目。

#### Scenario: 创建新分组
- **WHEN** 用户在侧边栏或设置中点击"新建分组"
- **THEN** 弹出分组名称输入对话框
- **AND** 用户输入分组名称后点击确认
- **AND** 分组被创建并显示在列表中

#### Scenario: 移动密码到分组
- **WHEN** 用户在密码条目上点击"移动到分组"
- **THEN** 显示分组选择列表
- **AND** 用户选择目标分组
- **AND** 条目被移动到指定分组

#### Scenario: 查看分组内的密码
- **WHEN** 用户点击某个分组
- **THEN** 仅显示该分组内的密码条目
- **AND** 显示"全部密码"选项可返回完整列表

### Requirement: 收藏功能

系统应允许用户收藏常用密码条目。

#### Scenario: 添加到收藏
- **WHEN** 用户在密码条目上点击收藏图标
- **THEN** 条目被标记为已收藏
- **AND** 收藏图标变为实心
- **AND** 条目可快速访问

#### Scenario: 查看收藏列表
- **WHEN** 用户点击"收藏"筛选选项
- **THEN** 仅显示已收藏的密码条目

### Requirement: 自动清除剪贴板

系统应在复制密码后自动清除剪贴板以保护安全。

#### Scenario: 复制密码后自动清除
- **WHEN** 用户复制任何敏感信息（密码、用户名等）
- **THEN** 启动 15 秒倒计时
- **AND** 15 秒后自动清除剪贴板内容
- **AND** 显示 Toast 提示"剪贴板已清除"

### Requirement: 生物识别解锁

系统应支持使用生物识别（指纹/面容）快速解锁应用。

#### Scenario: 启用生物识别
- **WHEN** 用户在设置中开启生物识别开关
- **THEN** 验证设备是否支持生物识别
- **THEN** 如支持，引导用户完成生物识别绑定
- **AND** 保存启用状态

#### Scenario: 使用生物识别解锁
- **WHEN** 用户打开应用且已启用生物识别
- **THEN** 显示生物识别认证界面
- **AND** 认证成功后自动解锁进入主页
- **AND** 认证失败后可输入主密码解锁

### Requirement: 自动锁定

系统应在无操作一段时间后自动锁定应用。

#### Scenario: 无操作超时锁定
- **WHEN** 用户开启自动锁定功能
- **AND** 用户在指定时间内无触摸操作
- **THEN** 应用自动锁定
- **AND** 显示锁屏界面要求重新验证

### Requirement: 冲突解决

同步时发生冲突应提供用户选择。

#### Scenario: 同步冲突处理
- **WHEN** 同步检测到本地与服务端数据冲突
- **THEN** 显示冲突解决对话框
- **AND** 显示冲突内容预览
- **AND** 用户可选择"保留本地"、"保留服务器"、"合并"三种策略

### Requirement: 截图防护

系统应防止在敏感页面截图。

#### Scenario: 禁止敏感页面截图
- **WHEN** 用户尝试对密码详情、设置等页面截图
- **THEN** 系统应阻止截图操作
- **AND** 显示安全警告提示

### Requirement: 数据导入导出

系统应支持导入和导出密码数据。

#### Scenario: 导出密码数据
- **WHEN** 用户在设置中点击"导出数据"
- **THEN** 显示导出选项（CSV、加密备份）
- **AND** 用户选择格式并确认
- **THEN** 生成导出文件并保存到本地

#### Scenario: 导入密码数据
- **WHEN** 用户点击"导入数据"
- **THEN** 显示文件选择器
- **AND** 验证文件格式
- **AND** 显示预览并确认导入

---

## MODIFIED Requirements

### Requirement: 密码强度评估

**原需求**：密码强度显示为 0-4 级

**修改为**：
- 评估维度：长度、字符多样性、常见模式检测
- 显示优化：显示详细评估结果和改进建议
- 实时反馈：在输入时即时更新强度评估

### Requirement: 搜索功能

**原需求**：支持按关键词搜索

**修改为**：
- 搜索字段：网站 URL、用户名、备注
- 搜索优化：模糊匹配、搜索历史
- 排序选项：按名称、时间、强度排序

---

## REMOVED Requirements

### Requirement: 简单密码提示

**原因**：该功能存在安全风险，已在安全评审中移除

**迁移**：用户应使用系统备忘录或专门的笔记应用记录提示信息

---

## 技术实现要点

### 依赖包更新

```yaml
dependencies:
  flutter:
    sdk: flutter
  flutter_secure_storage: ^9.0.0
  local_auth: ^2.2.0
  # 新增
  flutter_slidable: ^3.0.1
  share_plus: ^7.2.1
  file_picker: ^6.1.1
  csv: ^6.0.0
```

### 新增目录结构

```
lib/
├── core/
│   ├── generator/          # 新增：密码生成器
│   │   ├── password_generator.dart
│   │   └── generator.dart
│   └── security/           # 新增：安全相关
│       ├── screenshot_protection.dart
│       ├── jailbreak_detection.dart
│       ├── auto_lock_service.dart
│       └── security_service.dart
├── features/
│   ├── generator/          # 新增：密码生成器页面
│   │   └── password_generator_screen.dart
│   ├── group/              # 新增：分组管理
│   │   ├── groups_screen.dart
│   │   └── group_edit_dialog.dart
│   └── import_export/      # 新增：导入导出
│       ├── import_screen.dart
│       └── export_screen.dart
```

### 状态管理扩展

```dart
// 分组状态
class GroupState {
  final List<PasswordGroup> groups;
  final String? selectedGroupId;
  final bool isLoading;
}

// 密码生成器状态
class GeneratorState {
  final int length;
  final bool includeUppercase;
  final bool includeLowercase;
  final bool includeNumbers;
  final bool includeSpecial;
  final String generatedPassword;
}
```

---

## 里程碑规划

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| M1 | 密码生成器、自动清除剪贴板、收藏功能 | P0 |
| M2 | 分组管理、搜索优化 | P1 |
| M3 | 生物识别解锁、自动锁定 | P1 |
| M4 | 导入导出、冲突解决 | P2 |
| M5 | 安全加固（Root 检测、截图防护） | P2 |
