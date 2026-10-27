// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/domain/level.dart';
import '../data/mock_question_store.dart';
import '../domain/question_models.dart';

class QuestionBankState {
  const QuestionBankState({
    required this.records,
    this.query = 'find_pairs',
    this.type,
    this.topic,
    this.level,
    this.selectedId = 102,
  });

  final List<QuestionRecord> records;
  final String query;
  final QuestionType? type;
  final String? topic;
  final Level? level;
  final int? selectedId;

  static const totalRecords = 184;

  int get published => 159;

  int get drafts => 25;

  List<QuestionRecord> get visible {
    final q = query.trim().toLowerCase();
    return records.where((r) {
      if (q.isNotEmpty &&
          !r.title.toLowerCase().contains(q) &&
          !'#${r.id}'.contains(q)) {
        return false;
      }
      if (type != null && r.type != type) return false;
      if (topic != null && r.topic != topic) return false;
      if (level != null && r.level != level) return false;
      return true;
    }).toList();
  }

  QuestionRecord? get selected {
    for (final r in records) {
      if (r.id == selectedId) return r;
    }
    return null;
  }

  QuestionBankState copyWith({
    List<QuestionRecord>? records,
    String? query,
    Object? type = _keep,
    Object? topic = _keep,
    Object? level = _keep,
    Object? selectedId = _keep,
  }) {
    return QuestionBankState(
      records: records ?? this.records,
      query: query ?? this.query,
      type: identical(type, _keep) ? this.type : type as QuestionType?,
      topic: identical(topic, _keep) ? this.topic : topic as String?,
      level: identical(level, _keep) ? this.level : level as Level?,
      selectedId: identical(selectedId, _keep)
          ? this.selectedId
          : selectedId as int?,
    );
  }
}

const _keep = Object();

class QuestionBankController extends Notifier<QuestionBankState> {
  @override
  QuestionBankState build() => const QuestionBankState(records: seedQuestions);

  void setQuery(String value) => state = state.copyWith(query: value);

  void setType(QuestionType? value) => state = state.copyWith(type: value);

  void setTopic(String? value) => state = state.copyWith(topic: value);

  void setLevel(Level? value) => state = state.copyWith(level: value);

  void select(int? id) => state = state.copyWith(selectedId: id);

  void save(QuestionRecord updated) {
    state = state.copyWith(
      records: [
        for (final r in state.records) r.id == updated.id ? updated : r,
      ],
    );
  }

  void create() {
    final id =
        state.records.map((r) => r.id).fold<int>(100, (a, b) => a > b ? a : b) +
        1;
    final record = QuestionRecord(
      id: id,
      type: QuestionType.theory,
      title: 'Untitled question',
      updated: 'Updated just now',
      topic: 'Python Core',
      level: Level.junior,
      status: QuestionStatus.draft,
    );
    state = state.copyWith(
      records: [...state.records, record],
      query: '',
      selectedId: id,
    );
  }
}

final questionBankProvider =
    NotifierProvider<QuestionBankController, QuestionBankState>(
      QuestionBankController.new,
    );
