// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'interview_models.dart';

abstract class InterviewRepository {
  Future<InterviewSession> load(String id);

  Stream<ReplyEvent> reply(String id, String answer);

  Future<RunReport> run(String id, String code);
}
