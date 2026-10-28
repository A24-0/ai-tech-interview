// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'report_models.dart';

abstract class ReportRepository {
  Future<AssessmentReport> load(String id);
}
