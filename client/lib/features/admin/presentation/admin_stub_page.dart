// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../shell/presentation/shells.dart';

class AdminStubPage extends StatelessWidget {
  const AdminStubPage({super.key, required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return AdminScaffold(
      title: title,
      child: Center(
        child: Text(
          '$title will appear here in a later release.',
          style: TextStyle(color: c.textMuted),
        ),
      ),
    );
  }
}
