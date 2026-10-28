// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import '../../../core/domain/level.dart';
import '../domain/dashboard_data.dart';
import '../domain/dashboard_repository.dart';

class MockDashboardRepository implements DashboardRepository {
  @override
  Future<DashboardData> load() async {
    await Future<void>.delayed(const Duration(milliseconds: 250));
    return const DashboardData(
      today: 'Monday, 17 March 2025',
      draft: DraftSession(
        id: 'draft-1',
        title: 'Python Core — Middle',
        question: 4,
        totalQuestions: 8,
        elapsed: '12:45',
        savedAgo: '3 minutes ago',
      ),
      mastery: [
        TopicMastery(topic: 'Python Core', questionsPracticed: 18, score: 8.6),
        TopicMastery(topic: 'Algorithms', questionsPracticed: 14, score: 7.4),
        TopicMastery(
          topic: 'Data Structures',
          questionsPracticed: 9,
          score: 6.8,
        ),
        TopicMastery(topic: 'System Design', questionsPracticed: 4, score: 5.2),
      ],
      trend: [
        TrendPoint(label: '12 Feb', score: 5.2),
        TrendPoint(label: '19 Feb', score: 6.0),
        TrendPoint(label: '26 Feb', score: 7.1),
        TrendPoint(label: '07 Mar', score: 7.9),
        TrendPoint(label: '14 Mar', score: 8.8),
      ],
      trendDelta: 1.6,
      history: [
        ReportSummary(
          id: 'IS-8921',
          track: 'Python Core',
          level: Level.middle,
          date: '14 Mar 2025',
          durationMinutes: 52,
          score: 7.8,
          verdict: Verdict.ready,
        ),
        ReportSummary(
          id: 'IS-8874',
          track: 'Algorithms',
          level: Level.middle,
          date: '07 Mar 2025',
          durationMinutes: 47,
          score: 7.4,
          verdict: Verdict.developing,
        ),
        ReportSummary(
          id: 'IS-8792',
          track: 'Data Structures',
          level: Level.middle,
          date: '26 Feb 2025',
          durationMinutes: 45,
          score: 7.1,
          verdict: Verdict.developing,
        ),
        ReportSummary(
          id: 'IS-8655',
          track: 'Python Core',
          level: Level.junior,
          date: '19 Feb 2025',
          durationMinutes: 39,
          score: 6.8,
          verdict: Verdict.ready,
        ),
      ],
    );
  }
}
