// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';

import '../../interview/data/mock_interview_repository.dart';
import '../domain/report_models.dart';
import '../domain/report_repository.dart';

class MockReportRepository implements ReportRepository {
  @override
  Future<AssessmentReport> load(String id) async {
    await Future<void>.delayed(const Duration(milliseconds: 250));
    return AssessmentReport(
      id: id,
      track: 'Python Core — Middle',
      date: '14 March 2025',
      durationMinutes: 52,
      format: 'Theory + Coding',
      score: 7.8,
      verdictTitle: 'Ready for Middle',
      verdictText:
          'Strong fundamentals with one consistency gap in multi-pair handling.',
      prompts: 8,
      rubric: const [
        RubricScore(
          name: 'Problem solving',
          icon: Icons.psychology_outlined,
          score: 8.2,
          note: 'Clear decomposition and a sound hash-map approach.',
        ),
        RubricScore(
          name: 'Code quality',
          icon: Icons.code,
          score: 7.5,
          note: 'Readable typing and naming; edge case remains.',
        ),
        RubricScore(
          name: 'Communication',
          icon: Icons.chat_bubble_outline,
          score: 8.0,
          note: 'Concise reasoning with useful complexity analysis.',
        ),
        RubricScore(
          name: 'Core knowledge',
          icon: Icons.menu_book_outlined,
          score: 7.4,
          note: 'Good data model grasp; iterator detail was incomplete.',
        ),
      ],
      coding: const CodingReview(
        language: 'Python 3.12',
        passed: 2,
        total: 3,
        code: starterCode,
        complexity: 'O(n) time',
        timeMs: 38,
        memoryMb: 17.2,
        percentile: 72,
        findings: [
          Finding(
            tone: FindingTone.positive,
            title: 'Efficient core approach',
            text:
                'The single-pass hash map is appropriate for the input limit and was explained clearly.',
          ),
          Finding(
            tone: FindingTone.warning,
            title: 'Duplicate overwrite drops a pair',
            text:
                'seen[value] stores only the latest index, so [1, 2, 3, 4] misses (0, 3). Store a list of indices per value.',
          ),
        ],
      ),
      theory: const TheoryReview(
        question:
            'How does Python’s iterator protocol differ from an iterable?',
        answer:
            'An iterable exposes __iter__. An iterator also tracks state and produces values with __next__ until StopIteration.',
        score: 7.4,
        findings: [
          Finding(
            tone: FindingTone.positive,
            title: 'Accurate distinction',
            text:
                'You named the required protocol methods and termination behavior correctly.',
          ),
          Finding(
            tone: FindingTone.warning,
            title: 'Add one nuance',
            text:
                'Mention that __iter__ on an iterator returns self; an iterable may create a new iterator each time.',
          ),
        ],
      ),
    );
  }
}
