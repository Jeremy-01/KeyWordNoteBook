import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/password_group.dart';
import '../../data/repositories/group_repository.dart';
import 'group_edit_dialog.dart';

final groupRepositoryProvider = Provider<GroupRepository>((ref) {
  return GroupRepository();
});

class GroupsProvider extends StateNotifier<List<PasswordGroup>> {
  final GroupRepository _repository;

  GroupsProvider(this._repository) : super([]) {
    loadGroups();
  }

  Future<void> loadGroups() async {
    final groups = await _repository.getGroups();
    state = groups;
  }

  Future<void> createGroup(String name) async {
    await _repository.createGroup(name);
    await loadGroups();
  }

  Future<void> updateGroup(String id, String name) async {
    await _repository.updateGroup(id, name);
    await loadGroups();
  }

  Future<void> deleteGroup(String id) async {
    await _repository.deleteGroup(id);
    await loadGroups();
  }
}

final groupsProvider = StateNotifierProvider<GroupsProvider, List<PasswordGroup>>((ref) {
  final repository = ref.watch(groupRepositoryProvider);
  return GroupsProvider(repository);
});

class GroupsScreen extends ConsumerWidget {
  final String? selectedGroupId;
  final Function(String?)? onGroupSelected;

  const GroupsScreen({
    super.key,
    this.selectedGroupId,
    this.onGroupSelected,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groups = ref.watch(groupsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('分组管理'),
      ),
      body: groups.isEmpty
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(
                    Icons.folder_outlined,
                    size: 64,
                    color: Colors.grey,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    '暂无分组',
                    style: TextStyle(fontSize: 16, color: Colors.grey),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    '点击右下角按钮创建分组',
                    style: TextStyle(color: Colors.grey),
                  ),
                ],
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: groups.length,
              itemBuilder: (context, index) {
                final group = groups[index];
                return ListTile(
                  leading: const Icon(Icons.folder),
                  title: Text(group.name),
                  subtitle: Text('${group.itemCount} 个密码'),
                  trailing: PopupMenuButton<String>(
                    onSelected: (value) {
                      if (value == 'rename') {
                        _showEditDialog(context, ref, group);
                      } else if (value == 'delete') {
                        _showDeleteDialog(context, ref, group);
                      }
                    },
                    itemBuilder: (context) => [
                      const PopupMenuItem(
                        value: 'rename',
                        child: Row(
                          children: [
                            Icon(Icons.edit, size: 20),
                            SizedBox(width: 8),
                            Text('重命名'),
                          ],
                        ),
                      ),
                      const PopupMenuItem(
                        value: 'delete',
                        child: Row(
                          children: [
                            Icon(Icons.delete, size: 20, color: Colors.red),
                            SizedBox(width: 8),
                            Text('删除', style: TextStyle(color: Colors.red)),
                          ],
                        ),
                      ),
                    ],
                  ),
                  onTap: () {
                    if (onGroupSelected != null) {
                      onGroupSelected!(group.id);
                      Navigator.of(context).pop();
                    }
                  },
                );
              },
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCreateDialog(context, ref),
        child: const Icon(Icons.add),
      ),
    );
  }

  void _showCreateDialog(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => GroupEditDialog(
        onSave: (name) {
          ref.read(groupsProvider.notifier).createGroup(name);
        },
      ),
    );
  }

  void _showEditDialog(BuildContext context, WidgetRef ref, PasswordGroup group) {
    showDialog(
      context: context,
      builder: (context) => GroupEditDialog(
        initialName: group.name,
        onSave: (name) {
          ref.read(groupsProvider.notifier).updateGroup(group.id, name);
        },
      ),
    );
  }

  void _showDeleteDialog(BuildContext context, WidgetRef ref, PasswordGroup group) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('删除分组'),
        content: Text('确定要删除 "${group.name}" 分组吗？组内的密码将移至"未分组"。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.of(context).pop();
              await _migrateItemsToUngrouped(ref, group.id);
              ref.read(groupsProvider.notifier).deleteGroup(group.id);
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('删除'),
          ),
        ],
      ),
    );
  }

  Future<void> _migrateItemsToUngrouped(WidgetRef ref, String groupId) async {
    final keyBookNotifier = ref.read(keyBookProvider.notifier);
    final items = ref.read(keyBookProvider).items;

    for (final item in items) {
      if (item.groupId == groupId) {
        final updatedItem = item.copyWith(groupId: null);
        await keyBookNotifier.updateItem(item.index, updatedItem);
      }
    }
  }
}
