/// 主页 - 密码列表
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/providers/keybook_provider.dart';
import '../../data/models/key_item_model.dart';
import '../item/item_edit_screen.dart';
import '../item/item_detail_screen.dart';
import '../settings/settings_screen.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  final _searchController = TextEditingController();
  final _scrollController = ScrollController();
  bool _showScrollToTop = false;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    Future.microtask(() {
      ref.read(keyBookProvider.notifier).loadItems(refresh: true);
    });
  }

  void _onScroll() {
    final showButton = _scrollController.offset > 300;
    if (showButton != _showScrollToTop) {
      setState(() {
        _showScrollToTop = showButton;
      });
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToTop() {
    _scrollController.animateTo(
      0,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOut,
    );
  }

  @override
  Widget build(BuildContext context) {
    final keyBookState = ref.watch(keyBookProvider);
    final filteredItems = ref.watch(filteredItemsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('密码本'),
        actions: [
          IconButton(
            icon: const Icon(Icons.sync),
            onPressed: () {
              ref.read(keyBookProvider.notifier).loadItems(refresh: true);
            },
          ),
          PopupMenuButton<SortOption>(
            icon: const Icon(Icons.sort),
            onSelected: (option) {
              ref.read(keyBookProvider.notifier).setSortOption(option);
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: SortOption.name,
                child: Row(
                  children: [
                    if (keyBookState.sortOption == SortOption.name)
                      const Icon(Icons.check, size: 18),
                    const SizedBox(width: 8),
                    const Text('按名称排序'),
                  ],
                ),
              ),
              PopupMenuItem(
                value: SortOption.createdAt,
                child: Row(
                  children: [
                    if (keyBookState.sortOption == SortOption.createdAt)
                      const Icon(Icons.check, size: 18),
                    const SizedBox(width: 8),
                    const Text('按创建时间排序'),
                  ],
                ),
              ),
              PopupMenuItem(
                value: SortOption.updatedAt,
                child: Row(
                  children: [
                    if (keyBookState.sortOption == SortOption.updatedAt)
                      const Icon(Icons.check, size: 18),
                    const SizedBox(width: 8),
                    const Text('按更新时间排序'),
                  ],
                ),
              ),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const SettingsScreen()),
              );
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                TextField(
                  controller: _searchController,
                  decoration: InputDecoration(
                    hintText: '搜索密码...',
                    prefixIcon: const Icon(Icons.search),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 12,
                    ),
                  ),
                  onChanged: (value) {
                    ref.read(searchQueryProvider.notifier).state = value;
                  },
                ),
                const SizedBox(height: 12),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      FilterChip(
                        label: const Text('全部'),
                        selected: keyBookState.filterOption == FilterOption.all,
                        onSelected: (_) {
                          ref.read(keyBookProvider.notifier)
                              .setFilterOption(FilterOption.all);
                        },
                      ),
                      const SizedBox(width: 8),
                      FilterChip(
                        avatar: Icon(
                          keyBookState.filterOption == FilterOption.favorites
                              ? Icons.favorite
                              : Icons.favorite_border,
                          size: 18,
                        ),
                        label: const Text('收藏'),
                        selected: keyBookState.filterOption == FilterOption.favorites,
                        onSelected: (_) {
                          ref.read(keyBookProvider.notifier)
                              .setFilterOption(FilterOption.favorites);
                        },
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: _buildBody(keyBookState, filteredItems),
          ),
        ],
      ),
      floatingActionButton: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AnimatedOpacity(
            opacity: _showScrollToTop ? 1.0 : 0.0,
            duration: const Duration(milliseconds: 200),
            child: FloatingActionButton.small(
              heroTag: 'scrollToTop',
              onPressed: _showScrollToTop ? _scrollToTop : null,
              child: const Icon(Icons.keyboard_arrow_up),
            ),
          ),
          const SizedBox(height: 8),
          FloatingActionButton(
            heroTag: 'addItem',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => const ItemEditScreen(),
                ),
              );
            },
            child: const Icon(Icons.add),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(KeyBookState state, List<KeyItemModel> items) {
    if (state.isLoading && items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && items.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            Text(state.error!),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                ref.read(keyBookProvider.notifier).loadItems(refresh: true);
              },
              child: const Text('重试'),
            ),
          ],
        ),
      );
    }

    if (items.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.lock_outline, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            const Text(
              '暂无密码条目',
              style: TextStyle(fontSize: 16, color: Colors.grey),
            ),
            const SizedBox(height: 8),
            const Text(
              '点击下方 + 按钮添加',
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(keyBookProvider.notifier).loadItems(refresh: true);
      },
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: items.length,
        itemBuilder: (context, index) {
          final item = items[index];
          return _KeyItemCard(
            item: item,
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => ItemDetailScreen(itemId: item.index),
                ),
              );
            },
            onEdit: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => ItemEditScreen(item: item),
                ),
              );
            },
            onDelete: () => _showDeleteDialog(item),
            onToggleFavorite: () {
              ref.read(keyBookProvider.notifier).toggleFavorite(item.index);
            },
          );
        },
      ),
    );
  }

  Future<void> _showDeleteDialog(KeyItemModel item) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('删除确认'),
        content: Text('确定要删除 "${item.url}" 吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('删除'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await ref.read(keyBookProvider.notifier).deleteItem(item.index);
    }
  }
}

class _KeyItemCard extends StatelessWidget {
  final KeyItemModel item;
  final VoidCallback onTap;
  final VoidCallback onEdit;
  final VoidCallback onDelete;
  final VoidCallback onToggleFavorite;

  const _KeyItemCard({
    required this.item,
    required this.onTap,
    required this.onEdit,
    required this.onDelete,
    required this.onToggleFavorite,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: Theme.of(context).primaryColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Center(
                  child: Text(
                    _getSiteInitial(item.url),
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Theme.of(context).primaryColor,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            _getSiteName(item.url),
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w600,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (item.isFavorite)
                          const Icon(
                            Icons.favorite,
                            color: Colors.red,
                            size: 18,
                          ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      item.username,
                      style: TextStyle(
                        color: Colors.grey.shade600,
                        fontSize: 14,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              _buildPasswordStrengthIndicator(item.passwordLevel),
              PopupMenuButton<String>(
                onSelected: (value) {
                  if (value == 'edit') onEdit();
                  if (value == 'delete') onDelete();
                  if (value == 'favorite') onToggleFavorite();
                },
                itemBuilder: (context) => [
                  PopupMenuItem(
                    value: 'favorite',
                    child: Row(
                      children: [
                        Icon(
                          item.isFavorite ? Icons.favorite : Icons.favorite_border,
                          size: 20,
                          color: item.isFavorite ? Colors.red : null,
                        ),
                        const SizedBox(width: 8),
                        Text(item.isFavorite ? '取消收藏' : '收藏'),
                      ],
                    ),
                  ),
                  const PopupMenuItem(
                    value: 'edit',
                    child: Row(
                      children: [
                        Icon(Icons.edit, size: 20),
                        SizedBox(width: 8),
                        Text('编辑'),
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
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPasswordStrengthIndicator(int level) {
    final color = switch (level) {
      0 => Colors.red,
      1 => Colors.orange,
      2 => Colors.yellow.shade700,
      3 => Colors.lightGreen,
      4 => Colors.green,
      _ => Colors.grey,
    };

    return Container(
      width: 8,
      height: 40,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(4),
      ),
    );
  }

  String _getSiteName(String url) {
    try {
      final uri = Uri.parse(url);
      return uri.host.replaceFirst('www.', '');
    } catch (e) {
      return url;
    }
  }

  String _getSiteInitial(String url) {
    final name = _getSiteName(url);
    return name.isNotEmpty ? name[0].toUpperCase() : '?';
  }
}
