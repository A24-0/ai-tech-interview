// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

enum MessageRole { interviewer, candidate }

class DialogueMessage {
  const DialogueMessage({
    required this.role,
    required this.text,
    required this.time,
  });

  final MessageRole role;
  final String text;
  final String time;
}

class CodingTask {
  const CodingTask({
    required this.title,
    required this.difficulty,
    required this.constraints,
    required this.language,
    required this.statement,
    required this.starterCode,
  });

  final String title;
  final String difficulty;
  final String constraints;
  final String language;
  final String statement;
  final String starterCode;
}

class InterviewSession {
  const InterviewSession({
    required this.id,
    required this.title,
    required this.question,
    required this.totalQuestions,
    required this.elapsedSeconds,
    required this.messages,
    required this.task,
  });

  final String id;
  final String title;
  final int question;
  final int totalQuestions;
  final int elapsedSeconds;
  final List<DialogueMessage> messages;
  final CodingTask? task;
}

class TestCaseResult {
  const TestCaseResult({
    required this.name,
    required this.input,
    required this.expected,
    required this.received,
    required this.passed,
    required this.timeMs,
  });

  final String name;
  final String input;
  final String expected;
  final String received;
  final bool passed;
  final int timeMs;
}

class AstMetrics {
  const AstMetrics({
    required this.lines,
    required this.functions,
    required this.loops,
    required this.maxLoopDepth,
  });

  final int lines;
  final int functions;
  final int loops;
  final int maxLoopDepth;
}

sealed class ReplyEvent {
  const ReplyEvent();
}

class ReplyToken extends ReplyEvent {
  const ReplyToken(this.text);

  final String text;
}

class ReplyDone extends ReplyEvent {
  const ReplyDone({this.task, this.finished = false});

  final CodingTask? task;
  final bool finished;
}

class RunReport {
  const RunReport({
    required this.cases,
    required this.totalMs,
    required this.memoryMb,
    required this.metrics,
    this.error,
  });

  final List<TestCaseResult> cases;
  final int totalMs;
  final double memoryMb;
  final AstMetrics metrics;
  final String? error;

  int get passed => cases.where((c) => c.passed).length;

  int get failed => cases.length - passed;

  String get summary {
    if (error != null) return error!;
    if (failed == 0) return 'Execution result: all $passed passed';
    return 'Execution result: $passed passed, $failed failed';
  }
}
