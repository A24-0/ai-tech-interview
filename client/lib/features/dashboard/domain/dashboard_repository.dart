// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'dashboard_data.dart';

abstract class DashboardRepository {
  Future<DashboardData> load();
}
