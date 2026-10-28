// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'dart:convert';
import 'dart:math';

import 'package:dio/dio.dart';

import '../domain/interview_models.dart';
import '../domain/interview_repository.dart';

typedef StartRequest = ({int topicId, String level});

const _topicTitle = 'Python: основы';
const _questionLimits = {'junior': 3, 'middle': 4, 'senior': 5};

class InterviewApiException implements Exception {
  const InterviewApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

class ApiInterviewRepository implements InterviewRepository {
  ApiInterviewRepository(
    this._dio, {
    required this.start,
    this.pollInterval = const Duration(milliseconds: 700),
    this.pollTimeout = const Duration(seconds: 60),
  });

  final Dio _dio;
  final Future<StartRequest> Function() start;
  final Duration pollInterval;
  final Duration pollTimeout;

  @override
  Future<InterviewSession> load(String id) async {
    final active = await _dio.get<dynamic>('/interviews/active');
    if (active.statusCode == 200) return _session(active.data);
    if (active.statusCode != 404) throw _failure(active);
    if (id != 'new') {
      throw const InterviewApiException('There is no active interview');
    }
    final request = await start();
    final created = await _dio.post<dynamic>(
      '/interviews',
      data: {'topicId': request.topicId, 'level': request.level},
    );
    if (created.statusCode == 201) return _session(created.data);
    if (created.statusCode == 409) {
      final again = await _dio.get<dynamic>('/interviews/active');
      if (again.statusCode == 200) return _session(again.data);
    }
    throw _failure(created);
  }

  @override
  Stream<ReplyEvent> reply(String id, String answer) async* {
    final response = await _dio.post<String>(
      '/interviews/$id/messages',
      data: {'content': answer, 'clientMessageId': _uuid()},
      options: Options(responseType: ResponseType.plain),
    );
    if (response.statusCode != 200) throw _failure(response);
    for (final event in parseServerEvents(response.data ?? '')) {
      final data = event.data;
      switch (event.name) {
        case 'token':
          yield ReplyToken(data['text'] as String? ?? '');
        case 'done':
          final task = data['taskAssigned'];
          yield ReplyDone(
            task: task is Map<String, dynamic> ? _task(task) : null,
            finished: data['finished'] == true,
          );
        case 'error':
          throw InterviewApiException(
            data['message'] as String? ?? 'The interviewer is unavailable',
          );
      }
    }
  }

  @override
  Future<RunReport> run(String id, String code) async {
    final created = await _dio.post<dynamic>(
      '/interviews/$id/runs',
      data: {'code': code, 'clientRunId': _uuid()},
    );
    if (created.statusCode != 202 && created.statusCode != 200) {
      throw _failure(created);
    }
    final runId = (created.data as Map<String, dynamic>)['runId'] as String;
    final deadline = DateTime.now().add(pollTimeout);
    while (DateTime.now().isBefore(deadline)) {
      await Future<void>.delayed(pollInterval);
      final polled = await _dio.get<dynamic>('/runs/$runId');
      if (polled.statusCode != 200) throw _failure(polled);
      final run = polled.data as Map<String, dynamic>;
      switch (run['status']) {
        case 'done':
          return _report(run['result'] as Map<String, dynamic>);
        case 'failed':
          return _failed(run['error'] as String? ?? 'The run failed');
        case 'cancelled':
          return _failed('The run was cancelled');
      }
    }
    return _failed('The run did not finish in time');
  }

  InterviewSession _session(dynamic json) {
    final map = json as Map<String, dynamic>;
    final messages = [
      for (final m in (map['messages'] as List<dynamic>? ?? []))
        _message(m as Map<String, dynamic>),
    ];
    final level = map['level'] as String? ?? 'junior';
    final asked = messages
        .where((m) => m.role == MessageRole.interviewer)
        .length
        .clamp(1, 99);
    final started = messages.isEmpty
        ? null
        : DateTime.tryParse(
            ((map['messages'] as List).first as Map)['createdAt'] as String? ??
                '',
          );
    final task = map['task'];
    return InterviewSession(
      id: map['id'] as String,
      title: '$_topicTitle — ${level[0].toUpperCase()}${level.substring(1)}',
      question: asked,
      totalQuestions: _questionLimits[level] ?? 3,
      elapsedSeconds: started == null
          ? 0
          : DateTime.now().toUtc().difference(started.toUtc()).inSeconds,
      messages: messages,
      task: task is Map<String, dynamic> ? _task(task) : null,
    );
  }

  DialogueMessage _message(Map<String, dynamic> m) {
    final created = DateTime.tryParse(m['createdAt'] as String? ?? '');
    final local = created?.toLocal();
    return DialogueMessage(
      role: m['role'] == 'user'
          ? MessageRole.candidate
          : MessageRole.interviewer,
      text: m['content'] as String? ?? '',
      time: local == null
          ? ''
          : '${local.hour}:${local.minute.toString().padLeft(2, '0')}',
    );
  }

  CodingTask _task(Map<String, dynamic> t) => CodingTask(
    title: t['title'] as String? ?? 'Coding task',
    difficulty: 'Task',
    constraints: 'Write solve() so that every test passes',
    language: 'Python 3.12',
    statement: t['statement'] as String? ?? '',
    starterCode: t['starterCode'] as String? ?? '',
  );

  RunReport _report(Map<String, dynamic> result) {
    final tests = [
      for (final t in (result['tests'] as List<dynamic>? ?? []))
        _testCase(t as Map<String, dynamic>),
    ];
    final metrics = result['metrics'] as Map<String, dynamic>? ?? const {};
    final verdict = result['verdict'] as String?;
    return RunReport(
      cases: tests,
      totalMs: tests.fold(0, (sum, t) => sum + t.timeMs),
      memoryMb: 0,
      metrics: AstMetrics(
        lines: (metrics['lines'] as num?)?.toInt() ?? 0,
        functions: (metrics['functions'] as num?)?.toInt() ?? 0,
        loops: (metrics['loops'] as num?)?.toInt() ?? 0,
        maxLoopDepth: (metrics['maxLoopDepth'] as num?)?.toInt() ?? 0,
      ),
      error: switch (verdict) {
        'timeout' => 'Time limit exceeded',
        'error' when tests.isEmpty => _firstLine(
          result['stderr'] as String? ?? 'The code could not be run',
        ),
        _ => null,
      },
    );
  }

  TestCaseResult _testCase(Map<String, dynamic> t) => TestCaseResult(
    name: t['name'] as String? ?? 'Case',
    input: t['input'] as String? ?? '',
    expected: t['expected'] as String? ?? '—',
    received: t['actual'] as String? ?? t['error'] as String? ?? '—',
    passed: t['passed'] == true,
    timeMs: (t['timeMs'] as num?)?.toInt() ?? 0,
  );

  RunReport _failed(String message) => RunReport(
    cases: const [],
    totalMs: 0,
    memoryMb: 0,
    metrics: const AstMetrics(
      lines: 0,
      functions: 0,
      loops: 0,
      maxLoopDepth: 0,
    ),
    error: message,
  );

  String _firstLine(String text) => text.trim().split('\n').last;

  InterviewApiException _failure(Response<dynamic> response) {
    final data = response.data;
    final detail = data is Map ? data['detail'] : null;
    return InterviewApiException(
      detail is String ? detail : 'Server error ${response.statusCode}',
    );
  }
}

class ServerEvent {
  const ServerEvent(this.name, this.data);

  final String name;
  final Map<String, dynamic> data;
}

List<ServerEvent> parseServerEvents(String body) {
  final events = <ServerEvent>[];
  for (final block in body.split(RegExp(r'\r?\n\r?\n'))) {
    String? name;
    final data = StringBuffer();
    for (final line in block.split(RegExp(r'\r?\n'))) {
      if (line.startsWith('event:')) {
        name = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        data.write(line.substring(5).trim());
      }
    }
    if (name == null || data.isEmpty) continue;
    final decoded = jsonDecode(data.toString());
    if (decoded is Map<String, dynamic>) events.add(ServerEvent(name, decoded));
  }
  return events;
}

String _uuid() {
  final random = Random.secure();
  final bytes = List<int>.generate(16, (_) => random.nextInt(256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
}
