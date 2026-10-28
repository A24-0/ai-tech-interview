// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:interview_studio/features/interview/data/api_interview_repository.dart';
import 'package:interview_studio/features/interview/domain/interview_models.dart';

typedef Route = ({int status, Object? body, String type});

class FakeAdapter implements HttpClientAdapter {
  FakeAdapter(this.routes);

  final Map<String, List<Route>> routes;
  final calls = <String>[];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final key = '${options.method} ${options.path}';
    calls.add(key);
    final queue = routes[key];
    if (queue == null || queue.isEmpty) {
      return ResponseBody.fromString('{"detail":"no route"}', 500);
    }
    final route = queue.length > 1 ? queue.removeAt(0) : queue.first;
    final body = route.body is String
        ? route.body as String
        : jsonEncode(route.body);
    return ResponseBody.fromString(
      body,
      route.status,
      headers: {
        Headers.contentTypeHeader: [route.type],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

Route json(int status, Object? body) =>
    (status: status, body: body, type: 'application/json');

const sessionJson = {
  'id': 'abc',
  'status': 'active',
  'topicId': 1,
  'level': 'junior',
  'messages': [
    {
      'id': 1,
      'role': 'assistant',
      'content': 'Здравствуйте!',
      'createdAt': '2026-10-28T10:00:00Z',
    },
  ],
  'task': null,
};

ApiInterviewRepository repo(FakeAdapter adapter) {
  final dio = Dio(
    BaseOptions(baseUrl: 'http://api', validateStatus: (_) => true),
  )..httpClientAdapter = adapter;
  return ApiInterviewRepository(
    dio,
    start: () async => (topicId: 1, level: 'junior'),
    pollInterval: Duration.zero,
  );
}

void main() {
  test('load creates an interview when there is no active one', () async {
    final adapter = FakeAdapter({
      'GET /interviews/active': [
        json(404, {'code': 'no_active_session'}),
      ],
      'POST /interviews': [json(201, sessionJson)],
    });

    final session = await repo(adapter).load('new');

    expect(adapter.calls, ['GET /interviews/active', 'POST /interviews']);
    expect(session.id, 'abc');
    expect(session.messages.single.role, MessageRole.interviewer);
    expect(session.totalQuestions, 3);
    expect(session.task, isNull);
  });

  test(
    'load resumes the active interview without creating a new one',
    () async {
      final adapter = FakeAdapter({
        'GET /interviews/active': [json(200, sessionJson)],
      });

      await repo(adapter).load('draft-1');

      expect(adapter.calls, ['GET /interviews/active']);
    },
  );

  test('reply turns server events into tokens and the assigned task', () async {
    const stream =
        'event: token\ndata: {"text": "Хорошо, "}\n\n'
        'event: token\ndata: {"text": "дальше."}\n\n'
        'event: done\ndata: {"messageId": 3, "userMessageId": 2, "finished": false, '
        '"taskAssigned": {"id": 7, "title": "Сумма пар", "statement": "Найдите пару", '
        '"starterCode": "def solve(nums, k):\\n    ...", "language": "python"}}\n\n';
    final adapter = FakeAdapter({
      'POST /interviews/abc/messages': [
        (status: 200, body: stream, type: 'text/event-stream'),
      ],
    });

    final events = await repo(adapter).reply('abc', 'ответ').toList();

    expect(
      events.whereType<ReplyToken>().map((e) => e.text).join(),
      'Хорошо, дальше.',
    );
    final done = events.last as ReplyDone;
    expect(done.task?.title, 'Сумма пар');
    expect(done.task?.starterCode, startsWith('def solve'));
    expect(done.finished, isFalse);
  });

  test('an error event is thrown so the dialogue can offer a retry', () async {
    const stream =
        'event: error\ndata: {"code": "ai_unavailable", "message": "Модель временно недоступна", "retryable": true}\n\n';
    final adapter = FakeAdapter({
      'POST /interviews/abc/messages': [
        (status: 200, body: stream, type: 'text/event-stream'),
      ],
    });

    expect(
      repo(adapter).reply('abc', 'ответ').toList(),
      throwsA(isA<InterviewApiException>()),
    );
  });

  test('run polls until done and maps tests and metrics', () async {
    final adapter = FakeAdapter({
      'POST /interviews/abc/runs': [
        json(202, {'runId': 'r1', 'status': 'queued'}),
      ],
      'GET /runs/r1': [
        json(200, {'runId': 'r1', 'status': 'running'}),
        json(200, {
          'runId': 'r1',
          'status': 'done',
          'result': {
            'verdict': 'failed',
            'passed': 1,
            'total': 2,
            'tests': [
              {
                'name': 't1',
                'passed': true,
                'input': '[1], 2',
                'expected': 'True',
                'actual': 'True',
                'timeMs': 3,
              },
              {
                'name': 't2',
                'passed': false,
                'input': '[], 1',
                'expected': 'False',
                'actual': 'True',
                'timeMs': 4,
              },
            ],
            'metrics': {
              'lines': 5,
              'functions': 1,
              'loops': 2,
              'maxLoopDepth': 2,
            },
          },
        }),
      ],
    });

    final report = await repo(adapter).run('abc', 'def solve(): pass');

    expect(report.passed, 1);
    expect(report.failed, 1);
    expect(report.totalMs, 7);
    expect(report.metrics.loops, 2);
    expect(report.error, isNull);
    expect(adapter.calls.where((c) => c == 'GET /runs/r1').length, 2);
  });

  test('a timed out run is reported as an error', () async {
    final adapter = FakeAdapter({
      'POST /interviews/abc/runs': [
        json(202, {'runId': 'r2', 'status': 'queued'}),
      ],
      'GET /runs/r2': [
        json(200, {
          'runId': 'r2',
          'status': 'done',
          'result': {'verdict': 'timeout', 'tests': [], 'metrics': {}},
        }),
      ],
    });

    final report = await repo(adapter).run('abc', 'while True: pass');

    expect(report.error, 'Time limit exceeded');
  });

  test('parseServerEvents ignores incomplete blocks', () {
    final events = parseServerEvents(
      'event: token\ndata: {"text": "a"}\n\nevent: token\n\ndata: {"x":1}',
    );

    expect(events.length, 1);
    expect(events.single.data['text'], 'a');
  });
}
