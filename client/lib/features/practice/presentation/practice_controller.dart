// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/domain/level.dart';
import '../domain/topic.dart';

class PracticeState {
  const PracticeState({
    this.level = Level.middle,
    this.topicIds = const {1, 2},
  });

  final Level level;
  final Set<int> topicIds;

  List<Topic> get topics =>
      practiceTopics.where((t) => topicIds.contains(t.id)).toList();

  String get track => topics.isEmpty ? 'Not selected' : topics.first.title;

  bool get canStart => topicIds.isNotEmpty;

  PracticeState copyWith({Level? level, Set<int>? topicIds}) {
    return PracticeState(
      level: level ?? this.level,
      topicIds: topicIds ?? this.topicIds,
    );
  }
}

class PracticeController extends Notifier<PracticeState> {
  @override
  PracticeState build() => const PracticeState();

  void selectLevel(Level level) => state = state.copyWith(level: level);

  void toggleTopic(int id) {
    final next = {...state.topicIds};
    if (!next.remove(id)) next.add(id);
    state = state.copyWith(topicIds: next);
  }
}

final practiceControllerProvider =
    NotifierProvider<PracticeController, PracticeState>(PracticeController.new);
