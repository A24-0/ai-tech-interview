// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/mock_dashboard_repository.dart';
import '../domain/dashboard_data.dart';
import '../domain/dashboard_repository.dart';

final dashboardRepositoryProvider = Provider<DashboardRepository>(
  (ref) => MockDashboardRepository(),
);

final dashboardProvider = FutureProvider<DashboardData>(
  (ref) => ref.watch(dashboardRepositoryProvider).load(),
);
