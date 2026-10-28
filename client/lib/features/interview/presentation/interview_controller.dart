// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/api_config.dart';
import '../../practice/presentation/practice_controller.dart';
import '../data/api_interview_repository.dart';
import '../data/mock_interview_repository.dart';
import '../domain/interview_models.dart';
import '../domain/interview_repository.dart';

final interviewRepositoryProvider = Provider<InterviewRepository>((ref) {
  if (!apiEnabled) return MockInterviewRepository();
  return ApiInterviewRepository(
    ref.watch(dioProvider),
    start: () async {
      final practice = ref.read(practiceControllerProvider);
      return (topicId: 1, level: practice.level.apiValue);
    },
  );
});

class InterviewState {
  const InterviewState({
    this.session,
    this.task,
    this.messages = const [],
    this.streaming,
    this.running = false,
    this.report,
    this.elapsedSeconds = 0,
    this.error,
  });

  final InterviewSession? session;
  final CodingTask? task;
  final List<DialogueMessage> messages;
  final String? streaming;
  final bool running;
  final RunReport? report;
  final int elapsedSeconds;
  final String? error;

  bool get loading => session == null && error == null;

  bool get busy => streaming != null;

  InterviewState copyWith({
    InterviewSession? session,
    Object? task = _keep,
    List<DialogueMessage>? messages,
    Object? streaming = _keep,
    bool? running,
    Object? report = _keep,
    int? elapsedSeconds,
    Object? error = _keep,
  }) {
    return InterviewState(
      session: session ?? this.session,
      task: identical(task, _keep) ? this.task : task as CodingTask?,
      messages: messages ?? this.messages,
      streaming: identical(streaming, _keep)
          ? this.streaming
          : streaming as String?,
      running: running ?? this.running,
      report: identical(report, _keep) ? this.report : report as RunReport?,
      elapsedSeconds: elapsedSeconds ?? this.elapsedSeconds,
      error: identical(error, _keep) ? this.error : error as String?,
    );
  }
}

const _keep = Object();

class InterviewController extends Notifier<InterviewState> {
  InterviewController(this.id);

  final String id;
  Timer? _timer;

  @override
  InterviewState build() {
    ref.onDispose(() => _timer?.cancel());
    Future.microtask(_load);
    return const InterviewState();
  }

  String get _sessionId => state.session?.id ?? id;

  InterviewRepository get _repo => ref.read(interviewRepositoryProvider);

  Future<void> _load() async {
    try {
      final session = await _repo.load(id);
      state = state.copyWith(
        session: session,
        task: session.task,
        messages: session.messages,
        elapsedSeconds: session.elapsedSeconds,
      );
      _timer = Timer.periodic(const Duration(seconds: 1), (_) {
        state = state.copyWith(elapsedSeconds: state.elapsedSeconds + 1);
      });
    } catch (e) {
      state = state.copyWith(error: 'Could not load the interview: $e');
    }
  }

  Future<void> send(String text) async {
    final answer = text.trim();
    if (answer.isEmpty || state.busy) return;
    state = state.copyWith(
      messages: [
        ...state.messages,
        DialogueMessage(
          role: MessageRole.candidate,
          text: answer,
          time: _clock(),
        ),
      ],
      streaming: '',
    );
    var buffer = '';
    try {
      CodingTask? assigned;
      await for (final event in _repo.reply(_sessionId, answer)) {
        switch (event) {
          case ReplyToken(:final text):
            buffer += text;
            state = state.copyWith(streaming: buffer);
          case ReplyDone(:final task):
            assigned = task;
        }
      }
      state = state.copyWith(
        task: assigned ?? state.task,
        messages: [
          ...state.messages,
          DialogueMessage(
            role: MessageRole.interviewer,
            text: buffer.trim(),
            time: _clock(),
          ),
        ],
        streaming: null,
      );
    } catch (_) {
      state = state.copyWith(
        streaming: null,
        error: 'The interviewer is unavailable. Try sending your answer again.',
      );
    }
  }

  void dismissError() => state = state.copyWith(error: null);

  Future<void> run(String code) async {
    if (state.running) return;
    state = state.copyWith(running: true, report: null);
    try {
      final report = await _repo.run(_sessionId, code);
      state = state.copyWith(running: false, report: report);
    } catch (e) {
      state = state.copyWith(
        running: false,
        error: 'Could not run the code: $e',
      );
    }
  }

  String _clock() {
    final minutes = state.elapsedSeconds ~/ 60;
    final hours = 12 + minutes ~/ 60;
    return '$hours:${(minutes % 60).toString().padLeft(2, '0')}';
  }
}

final interviewControllerProvider =
    NotifierProvider.family<InterviewController, InterviewState, String>(
      InterviewController.new,
    );
