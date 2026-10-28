// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import '../../../core/domain/level.dart';

enum QuestionType { theory, coding }

enum QuestionStatus { published, draft }

class QuestionRecord {
  const QuestionRecord({
    required this.id,
    required this.type,
    required this.title,
    required this.updated,
    required this.topic,
    required this.level,
    required this.status,
    this.timeLimitSeconds = 2,
    this.memoryLimitMb = 128,
    this.starterCode = '',
    this.tests = '',
  });

  final int id;
  final QuestionType type;
  final String title;
  final String updated;
  final String topic;
  final Level level;
  final QuestionStatus status;
  final int timeLimitSeconds;
  final int memoryLimitMb;
  final String starterCode;
  final String tests;

  QuestionRecord copyWith({
    String? title,
    String? topic,
    Level? level,
    QuestionStatus? status,
    int? timeLimitSeconds,
    int? memoryLimitMb,
    String? starterCode,
    String? tests,
  }) {
    return QuestionRecord(
      id: id,
      type: type,
      title: title ?? this.title,
      updated: updated,
      topic: topic ?? this.topic,
      level: level ?? this.level,
      status: status ?? this.status,
      timeLimitSeconds: timeLimitSeconds ?? this.timeLimitSeconds,
      memoryLimitMb: memoryLimitMb ?? this.memoryLimitMb,
      starterCode: starterCode ?? this.starterCode,
      tests: tests ?? this.tests,
    );
  }
}
