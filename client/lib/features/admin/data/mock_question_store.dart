// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import '../../../core/domain/level.dart';
import '../domain/question_models.dart';

const _twoSumStarter =
    '''def find_pairs(nums: list[int], target: int) -> list[tuple[int, int]]:
    """Return all index pairs whose values sum to target."""
    # Write your solution here
    pass''';

const _twoSumTests = '''[
  { "nums": [2, 7, 11, 15], "target": 9,
    "expected": [[0, 1]] },
  { "nums": [3, 3], "target": 6,
    "expected": [[0, 1]] },
  { "nums": [1, 2, 3, 4], "target": 5,
    "expected": [[0, 3], [1, 2]] }
]''';

const seedQuestions = [
  QuestionRecord(
    id: 101,
    type: QuestionType.theory,
    title: 'Iterable vs. iterator protocol',
    updated: 'Updated 12 Mar 2025',
    topic: 'Python Core',
    level: Level.middle,
    status: QuestionStatus.published,
  ),
  QuestionRecord(
    id: 102,
    type: QuestionType.coding,
    title: 'find_pairs — Two Sum variant',
    updated: 'Updated 14 Mar 2025',
    topic: 'Algorithms',
    level: Level.middle,
    status: QuestionStatus.published,
    starterCode: _twoSumStarter,
    tests: _twoSumTests,
  ),
  QuestionRecord(
    id: 103,
    type: QuestionType.theory,
    title: 'Database transaction isolation',
    updated: 'Updated 10 Mar 2025',
    topic: 'SQL & Databases',
    level: Level.senior,
    status: QuestionStatus.draft,
  ),
  QuestionRecord(
    id: 104,
    type: QuestionType.coding,
    title: 'LRU cache with TTL',
    updated: 'Updated 08 Mar 2025',
    topic: 'Data Structures',
    level: Level.senior,
    status: QuestionStatus.published,
    timeLimitSeconds: 3,
    starterCode:
        'class LRUCache:\n    def __init__(self, capacity: int, ttl: float) -> None:\n        ...',
    tests: '[]',
  ),
];
