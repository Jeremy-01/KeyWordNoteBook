import 'package:flutter/material.dart';
import '../../data/models/key_item_model.dart';

enum ConflictResolutionStrategy {
  keepLocal,
  keepServer,
  merge,
}

class ConflictDialog extends StatefulWidget {
  final KeyItemModel localItem;
  final KeyItemModel serverItem;
  final Function(ConflictResolutionStrategy) onResolve;

  const ConflictDialog({
    super.key,
    required this.localItem,
    required this.serverItem,
    required this.onResolve,
  });

  @override
  State<ConflictDialog> createState() => _ConflictDialogState();
}

class _ConflictDialogState extends State<ConflictDialog> {
  ConflictResolutionStrategy _selectedStrategy = ConflictResolutionStrategy.keepServer;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.warning_amber, color: Colors.orange),
          SizedBox(width: 8),
          Text('同步冲突'),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              '检测到以下密码条目存在冲突，请选择解决方式：',
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 16),
            _buildComparisonCard('本地版本', widget.localItem, Colors.blue),
            const SizedBox(height: 12),
            _buildComparisonCard('服务器版本', widget.serverItem, Colors.green),
            const SizedBox(height: 16),
            const Text(
              '选择解决策略：',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            _buildStrategyOption(
              ConflictResolutionStrategy.keepLocal,
              '保留本地版本',
              '使用本地数据覆盖服务器',
            ),
            _buildStrategyOption(
              ConflictResolutionStrategy.keepServer,
              '保留服务器版本',
              '使用服务器数据覆盖本地',
            ),
            _buildStrategyOption(
              ConflictResolutionStrategy.merge,
              '合并',
              '手动合并两个版本',
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('取消'),
        ),
        ElevatedButton(
          onPressed: () {
            Navigator.of(context).pop(_selectedStrategy);
          },
          child: const Text('确认'),
        ),
      ],
    );
  }

  Widget _buildComparisonCard(String title, KeyItemModel item, Color color) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 4,
                  height: 20,
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: color,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            _buildField('网站', item.url),
            _buildField('用户名', item.username),
            if (item.note.isNotEmpty) _buildField('备注', item.note),
            if (item.updatedAt != null)
              _buildField(
                '更新时间',
                '${item.updatedAt!.year}-${item.updatedAt!.month.toString().padLeft(2, '0')}-${item.updatedAt!.day.toString().padLeft(2, '0')} ${item.updatedAt!.hour.toString().padLeft(2, '0')}:${item.updatedAt!.minute.toString().padLeft(2, '0')}',
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildField(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 60,
            child: Text(
              '$label:',
              style: const TextStyle(
                color: Colors.grey,
                fontSize: 12,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 12),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStrategyOption(
    ConflictResolutionStrategy strategy,
    String title,
    String description,
  ) {
    final isSelected = _selectedStrategy == strategy;
    return InkWell(
      onTap: () => setState(() => _selectedStrategy = strategy),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
        decoration: BoxDecoration(
          border: Border.all(
            color: isSelected ? Theme.of(context).primaryColor : Colors.grey.shade300,
            width: isSelected ? 2 : 1,
          ),
          borderRadius: BorderRadius.circular(8),
          color: isSelected
              ? Theme.of(context).primaryColor.withOpacity(0.05)
              : null,
        ),
        child: Row(
          children: [
            Radio<ConflictResolutionStrategy>(
              value: strategy,
              groupValue: _selectedStrategy,
              onChanged: (value) => setState(() => _selectedStrategy = value!),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.w500),
                  ),
                  Text(
                    description,
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey.shade600,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

Future<ConflictResolutionStrategy?> showConflictDialog(
  BuildContext context, {
  required KeyItemModel localItem,
  required KeyItemModel serverItem,
}) {
  return showDialog<ConflictResolutionStrategy>(
    context: context,
    barrierDismissible: false,
    builder: (context) => ConflictDialog(
      localItem: localItem,
      serverItem: serverItem,
      onResolve: (strategy) => Navigator.of(context).pop(strategy),
    ),
  );
}
