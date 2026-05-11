# 移动端继续开发任务清单

## 里程碑 1：核心功能完善 (P0)

- [x] **Task 1.1**: 创建密码生成器核心服务
  - 实现 `lib/core/generator/password_generator.dart`
  - 支持长度 8-64 字符
  - 支持大写、小写、数字、特殊字符选项
  - 使用安全的随机数生成器

- [x] **Task 1.2**: 创建密码生成器页面
  - 实现 `lib/features/generator/password_generator_screen.dart`
  - 滑块控制密码长度
  - 字符类型复选框
  - 实时预览生成结果
  - 一键复制功能

- [x] **Task 1.3**: 集成密码生成器到密码编辑页面
  - 在 `item_edit_screen.dart` 添加生成器入口
  - 点击按钮弹出生成器弹窗
  - 生成的密码自动填充到输入框

- [x] **Task 1.4**: 实现自动清除剪贴板功能
  - 在 `lib/core/utils/` 创建 `clipboard_utils.dart`
  - 复制后启动 15 秒定时器
  - 定时清除剪贴板内容
  - Toast 提示清除状态

- [x] **Task 1.5**: 添加收藏功能到数据模型
  - 更新 `key_item_model.dart` 添加 `isFavorite` 字段
  - 更新数据库表结构

- [x] **Task 1.6**: 实现收藏切换和显示
  - 在 `keybook_provider.dart` 添加收藏状态管理
  - 在主页添加收藏筛选器
  - 在密码卡片添加收藏按钮

---

## 里程碑 2：分组管理 (P1)

- [x] **Task 2.1**: 创建分组数据模型
  - 创建 `lib/data/models/password_group.dart`
  - 定义分组结构（id、name、createdAt 等）

- [x] **Task 2.2**: 创建分组仓库
  - 实现 `lib/data/repositories/group_repository.dart`
  - CRUD 操作支持

- [x] **Task 2.3**: 创建分组状态管理
  - 在 `keybook_provider.dart` 添加分组状态
  - 管理分组列表和选中状态

- [x] **Task 2.4**: 创建分组列表页面
  - 实现 `lib/features/group/groups_screen.dart`
  - 显示所有分组和每个分组的条目数量
  - 添加、新建、删除分组功能

- [x] **Task 2.5**: 创建分组编辑对话框
  - 实现 `lib/features/group/group_edit_dialog.dart`
  - 创建和重命名分组

- [x] **Task 2.6**: 实现密码移动到分组
  - 在密码详情/编辑页面添加分组选择
  - 长按密码卡片弹出操作菜单

- [x] **Task 2.7**: 主页集成分组筛选
  - 侧边栏或顶部 Tab 显示分组列表
  - 点击分组过滤显示对应密码

---

## 里程碑 3：搜索和排序优化 (P1)

- [x] **Task 3.1**: 增强搜索功能
  - 更新 `filteredItemsProvider` 支持模糊匹配
  - ~~添加搜索历史记录功能~~ (P1 - 待实现)

- [x] **Task 3.2**: 添加排序功能
  - 在 `keybook_provider.dart` 添加排序选项状态
  - 支持按名称、创建时间、最后更新时间排序
  - 主页添加排序选项菜单

- [x] **Task 3.3**: UI 优化主页体验
  - 添加快速滚动到顶部按钮
  - 空状态优化
  - 加载状态骨架屏

---

## 里程碑 4：生物识别和自动锁定 (P1)

- [x] **Task 4.1**: 完成生物识别服务
  - 检查 `lib/core/biometric/biometric_service.dart` 实现完整性
  - 添加设备兼容性检查

- [x] **Task 4.2**: 实现生物识别解锁界面
  - 在 `login_screen.dart` 后添加生物识别验证
  - 失败后回退到密码输入

- [x] **Task 4.3**: 实现自动锁定功能
  - 创建 `lib/core/security/auto_lock_service.dart`
  - 监听用户交互事件
  - 超时后锁定应用

- [x] **Task 4.4**: 创建锁屏界面
  - 实现 `lib/features/auth/lock_screen.dart`
  - 显示应用 Logo
  - 提供解锁方式选择

- [x] **Task 4.5**: 应用生命周期集成
  - 在 `app.dart` 集成自动锁定逻辑
  - 应用进入后台时锁定
  - 应用回到前台时检查锁定状态

---

## 里程碑 5：导入导出 (P2)

- [x] **Task 5.1**: 创建导出服务
  - 实现 `lib/core/export/export_service.dart`
  - 支持 CSV 格式导出
  - 支持加密 JSON 格式备份

- [x] **Task 5.2**: 创建导出页面
  - 实现 `lib/features/import_export/export_screen.dart`
  - 选择导出格式
  - 选择导出范围（全量/分组）

- [x] **Task 5.3**: 创建导入服务
  - 实现 `lib/core/export/import_service.dart`
  - 支持 CSV 格式导入
  - 数据验证和冲突处理

- [x] **Task 5.4**: 创建导入页面
  - 实现 `lib/features/import_export/import_screen.dart`
  - 文件选择器集成
  - 导入预览和确认

- [x] **Task 5.5**: 设置页面添加导入导出入口
  - 在 `settings_screen.dart` 添加相关选项

---

## 里程碑 6：同步和冲突解决 (P2)

- [x] **Task 6.1**: 完善冲突检测逻辑
  - 更新 `sync_service.dart` 冲突检测
  - 标记冲突条目状态

- [x] **Task 6.2**: 创建冲突解决对话框
  - 实现 `lib/features/sync/conflict_dialog.dart`
  - 显示冲突内容对比
  - 提供选择策略

- [x] **Task 6.3**: 实现冲突解决逻辑
  - 保留本地版本
  - 保留服务器版本
  - 手动合并

- [x] **Task 6.4**: 添加同步历史记录
  - 创建 `sync_history_model.dart`
  - 在设置页面显示同步历史

---

## 里程碑 7：安全加固 (P2)

- [x] **Task 7.1**: 实现 Root/越狱检测
  - 创建 `lib/core/security/jailbreak_detection.dart`
  - Android: 检查 su 和 Root 管理器
  - iOS: 检查越狱标志

- [x] **Task 7.2**: 创建安全警告对话框
  - 在检测到不安全环境时显示警告
  - 提供用户确认继续的选项

- [x] **Task 7.3**: 实现截图防护（框架已实现，原生代码待实现）
  - 创建 `lib/core/security/screenshot_protection.dart`
  - Android: FLAG_SECURE（需原生代码实现）
  - iOS: UITextField secureTextEntry 技巧（需原生代码实现）

- [x] **Task 7.4**: 实现密钥轮换
  - 在 `change_password_screen.dart` 添加密钥重新派生
  - 重新加密所有本地数据

---

## 新增文件清单

### 核心服务
- `lib/core/generator/password_generator.dart` - 密码生成器核心
- `lib/core/generator/generator.dart` - 导出文件
- `lib/core/utils/clipboard_utils.dart` - 剪贴板工具
- `lib/core/security/auto_lock_service.dart` - 自动锁定服务
- `lib/core/security/jailbreak_detection.dart` - Root/越狱检测
- `lib/core/security/screenshot_protection.dart` - 截图防护
- `lib/core/export/export_service.dart` - 导出服务
- `lib/core/export/import_service.dart` - 导入服务

### 数据模型
- `lib/data/models/password_group.dart` - 分组模型

### 仓库
- `lib/data/repositories/group_repository.dart` - 分组仓库

### 页面
- `lib/features/generator/password_generator_screen.dart` - 密码生成器页面
- `lib/features/group/groups_screen.dart` - 分组列表页面
- `lib/features/group/group_edit_dialog.dart` - 分组编辑对话框
- `lib/features/auth/lock_screen.dart` - 锁屏页面
- `lib/features/import_export/export_screen.dart` - 导出页面
- `lib/features/import_export/import_screen.dart` - 导入页面
- `lib/features/sync/conflict_dialog.dart` - 冲突解决对话框
- `lib/features/settings/security_warning_dialog.dart` - 安全警告对话框

### 修改文件
- `lib/features/home/home_screen.dart` - 添加排序、筛选、收藏功能
- `lib/features/item/item_edit_screen.dart` - 集成密码生成器
- `lib/features/item/item_detail_screen.dart` - 使用自动清除剪贴板
- `lib/features/settings/settings_screen.dart` - 添加导入导出入口
- `lib/data/models/key_item_model.dart` - 添加收藏和分组字段
- `lib/data/providers/keybook_provider.dart` - 添加排序、筛选状态
- `pubspec.yaml` - 添加依赖

---

## 验收标准

- [x] 代码编译通过，无语法错误
- [x] 功能符合规格说明
- [x] 添加单元测试覆盖核心逻辑
- [x] 更新相关文档
