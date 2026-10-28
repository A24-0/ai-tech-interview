// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../theme/app_colors.dart';
import 'common.dart';

class NavItem {
  const NavItem(this.label, this.icon, this.route);

  final String label;
  final IconData icon;
  final String route;
}

class ShellUser {
  const ShellUser({
    required this.name,
    required this.subtitle,
    required this.initials,
  });

  final String name;
  final String subtitle;
  final String initials;
}

const _wideBreakpoint = 880.0;

class AppShell extends StatelessWidget {
  const AppShell({
    super.key,
    required this.items,
    required this.currentRoute,
    required this.brandSubtitle,
    required this.user,
    required this.title,
    required this.child,
    this.subtitle,
    this.actions = const [],
    this.onUserTap,
  });

  final List<NavItem> items;
  final String currentRoute;
  final String brandSubtitle;
  final ShellUser user;
  final String title;
  final String? subtitle;
  final List<Widget> actions;
  final Widget child;
  final VoidCallback? onUserTap;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final wide = MediaQuery.sizeOf(context).width >= _wideBreakpoint;
    final sidebar = _Sidebar(
      items: items,
      currentRoute: currentRoute,
      brandSubtitle: brandSubtitle,
      user: user,
      onUserTap: onUserTap,
    );
    return Scaffold(
      backgroundColor: c.background,
      drawer: wide
          ? null
          : Drawer(
              backgroundColor: c.background,
              child: SafeArea(child: sidebar),
            ),
      body: Row(
        children: [
          if (wide) SizedBox(width: 232, child: sidebar),
          if (wide) VerticalDivider(width: 1, color: c.border),
          Expanded(
            child: Column(
              children: [
                _Header(
                  title: title,
                  subtitle: subtitle,
                  actions: actions,
                  showMenu: !wide,
                ),
                Divider(height: 1, color: c.border),
                Expanded(child: child),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({
    required this.title,
    required this.subtitle,
    required this.actions,
    required this.showMenu,
  });

  final String title;
  final String? subtitle;
  final List<Widget> actions;
  final bool showMenu;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Container(
      height: 67,
      color: c.surface,
      padding: const EdgeInsets.symmetric(horizontal: 28),
      child: Row(
        children: [
          if (showMenu)
            Builder(
              builder: (context) => IconButton(
                icon: const Icon(Icons.menu),
                onPressed: () => Scaffold.of(context).openDrawer(),
              ),
            ),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                ),
                if (subtitle != null)
                  Text(subtitle!, style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
          for (final a in actions) ...[const SizedBox(width: 10), a],
        ],
      ),
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({
    required this.items,
    required this.currentRoute,
    required this.brandSubtitle,
    required this.user,
    required this.onUserTap,
  });

  final List<NavItem> items;
  final String currentRoute;
  final String brandSubtitle;
  final ShellUser user;
  final VoidCallback? onUserTap;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Container(
      color: c.background,
      padding: const EdgeInsets.fromLTRB(16, 22, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(left: 6),
            child: Row(
              children: [
                const BrandMark(size: 30),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Interview Studio',
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                      Text(
                        brandSubtitle,
                        style: Theme.of(
                          context,
                        ).textTheme.bodySmall?.copyWith(fontSize: 11),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 22),
          for (final item in items)
            _NavTile(
              item: item,
              selected:
                  currentRoute == item.route ||
                  currentRoute.startsWith('${item.route}/'),
            ),
          const Spacer(),
          InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: onUserTap,
            child: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: c.surface,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: c.border),
              ),
              child: Row(
                children: [
                  Avatar(user.initials),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          user.name,
                          style: Theme.of(
                            context,
                          ).textTheme.titleSmall?.copyWith(fontSize: 13),
                        ),
                        Text(
                          user.subtitle,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(
                            context,
                          ).textTheme.bodySmall?.copyWith(fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.more_horiz, size: 18, color: c.textFaint),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _NavTile extends StatelessWidget {
  const _NavTile({required this.item, required this.selected});

  final NavItem item;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Material(
        color: selected ? c.surfaceMuted : Colors.transparent,
        borderRadius: BorderRadius.circular(10),
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: () => context.go(item.route),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
            child: Row(
              children: [
                Icon(
                  item.icon,
                  size: 18,
                  color: selected ? c.text : c.textMuted,
                ),
                const SizedBox(width: 12),
                Text(
                  item.label,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                    color: selected ? c.text : c.textMuted,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
