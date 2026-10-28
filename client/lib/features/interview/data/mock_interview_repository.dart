// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import '../domain/interview_models.dart';
import '../domain/interview_repository.dart';

const starterCode =
    '''def find_pairs(nums: list[int], target: int) -> list[tuple[int, int]]:
    seen: dict[int, int] = {}
    pairs: list[tuple[int, int]] = []

    for index, value in enumerate(nums):
        complement = target - value
        if complement in seen:
            pairs.append((seen[complement], index))
        seen[value] = index

    return pairs''';

class MockInterviewRepository implements InterviewRepository {
  MockInterviewRepository({this.tokenDelay = const Duration(milliseconds: 40)});

  final Duration tokenDelay;

  static const _astMetrics = AstMetrics(
    complexity: 3,
    functions: 1,
    branches: 2,
    maxDepth: 3,
  );

  @override
  Future<InterviewSession> load(String id) async {
    await Future<void>.delayed(const Duration(milliseconds: 200));
    return const InterviewSession(
      id: 'draft-1',
      title: 'Python Core — Middle',
      question: 4,
      totalQuestions: 8,
      elapsedSeconds: 12 * 60 + 45,
      messages: [
        DialogueMessage(
          role: MessageRole.interviewer,
          time: '12:02',
          text:
              'Let’s move to a coding task. Implement find_pairs: return every pair of indices whose values sum to target. Explain your approach before you code.',
        ),
        DialogueMessage(
          role: MessageRole.candidate,
          time: '12:20',
          text:
              'I’ll use a hash map from value to index. For each number, I check whether target minus the number has already been seen. That gives O(n) time and O(n) space.',
        ),
        DialogueMessage(
          role: MessageRole.interviewer,
          time: '12:31',
          text:
              'Good. Consider duplicate values and multiple valid pairs. Please preserve index order and avoid pairing an element with itself.',
        ),
      ],
      task: CodingTask(
        title: 'find_pairs — Two Sum variant',
        difficulty: 'Medium',
        constraints: 'Return all index pairs · 1 ≤ len(nums) ≤ 10⁵',
        language: 'Python 3.12',
        statement:
            'Given a list of integers nums and an integer target, return every pair of indices (i, j) with i < j whose values sum to target. '
            'Pairs must be ordered by j, then by i. The same element cannot be used twice.',
        starterCode: starterCode,
      ),
    );
  }

  @override
  Stream<String> reply(String id, String answer) async* {
    const words = [
      'Thanks,',
      'that',
      'is',
      'a',
      'clear',
      'explanation.',
      'Walk',
      'me',
      'through',
      'what',
      'happens',
      'when',
      'the',
      'list',
      'contains',
      'duplicate',
      'values',
      'such',
      'as',
      '[1, 2, 3, 4]',
      'with',
      'target',
      '5.',
    ];
    for (final word in words) {
      await Future<void>.delayed(tokenDelay);
      yield '$word ';
    }
  }

  @override
  Future<RunReport> run(String id, String code) async {
    await Future<void>.delayed(const Duration(milliseconds: 600));
    if (code.trim().isEmpty) {
      return const RunReport(
        cases: [],
        totalMs: 0,
        memoryMb: 0,
        metrics: _astMetrics,
        error: 'Nothing to run: the editor is empty',
      );
    }
    if (code.contains('while True')) {
      return const RunReport(
        cases: [],
        totalMs: 5000,
        memoryMb: 0,
        metrics: _astMetrics,
        error: 'Time limit exceeded after 5 s',
      );
    }
    return const RunReport(
      totalMs: 38,
      memoryMb: 17.2,
      metrics: _astMetrics,
      cases: [
        TestCaseResult(
          name: 'Case 1',
          input: '[2, 7, 11, 15], 9',
          expected: '[(0, 1)]',
          received: '[(0, 1)]',
          passed: true,
          timeMs: 11,
        ),
        TestCaseResult(
          name: 'Case 2',
          input: '[3, 3], 6',
          expected: '[(0, 1)]',
          received: '[(0, 1)]',
          passed: true,
          timeMs: 9,
        ),
        TestCaseResult(
          name: 'Case 3',
          input: '[1, 2, 3, 4], 5',
          expected: '[(0, 3), (1, 2)]',
          received: '[(1, 2)]',
          passed: false,
          timeMs: 18,
        ),
      ],
    );
  }
}
