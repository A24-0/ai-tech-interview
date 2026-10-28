// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import '../../../core/domain/level.dart';

enum Verdict {
  ready('Ready'),
  developing('Developing');

  const Verdict(this.label);

  final String label;
}

class TopicMastery {
  const TopicMastery({
    required this.topic,
    required this.questionsPracticed,
    required this.score,
  });

  final String topic;
  final int questionsPracticed;
  final double score;
}

class TrendPoint {
  const TrendPoint({required this.label, required this.score});

  final String label;
  final double score;
}

class ReportSummary {
  const ReportSummary({
    required this.id,
    required this.track,
    required this.level,
    required this.date,
    required this.durationMinutes,
    required this.score,
    required this.verdict,
  });

  final String id;
  final String track;
  final Level level;
  final String date;
  final int durationMinutes;
  final double score;
  final Verdict verdict;

  String get verdictLabel =>
      verdict == Verdict.ready ? 'Ready for ${level.label}' : verdict.label;
}

class DraftSession {
  const DraftSession({
    required this.id,
    required this.title,
    required this.question,
    required this.totalQuestions,
    required this.elapsed,
    required this.savedAgo,
  });

  final String id;
  final String title;
  final int question;
  final int totalQuestions;
  final String elapsed;
  final String savedAgo;
}

class DashboardData {
  const DashboardData({
    required this.today,
    required this.draft,
    required this.mastery,
    required this.trend,
    required this.trendDelta,
    required this.history,
  });

  final String today;
  final DraftSession? draft;
  final List<TopicMastery> mastery;
  final List<TrendPoint> trend;
  final double trendDelta;
  final List<ReportSummary> history;
}
