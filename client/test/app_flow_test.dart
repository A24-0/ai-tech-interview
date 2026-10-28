// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:interview_studio/app.dart';
import 'package:interview_studio/features/auth/data/mock_auth_repository.dart';
import 'package:interview_studio/features/auth/presentation/auth_controller.dart';
import 'package:interview_studio/features/interview/data/mock_interview_repository.dart';
import 'package:interview_studio/features/interview/presentation/interview_controller.dart';

Future<void> openApp(WidgetTester tester) async {
  // The test font has no real glyph metrics, so text is wider than in the app: ignore overflow reports only.
  final onError = FlutterError.onError;
  FlutterError.onError = (details) {
    if (details.exceptionAsString().contains('overflowed')) return;
    onError?.call(details);
  };
  addTearDown(() => FlutterError.onError = onError);
  tester.view.physicalSize = const Size(1440, 1100);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        authRepositoryProvider.overrideWithValue(
          MockAuthRepository(delay: Duration.zero),
        ),
        interviewRepositoryProvider.overrideWithValue(
          MockInterviewRepository(tokenDelay: Duration.zero),
        ),
      ],
      child: const InterviewStudioApp(),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> signIn(WidgetTester tester, String email, String password) async {
  await tester.enterText(find.byType(TextField).at(0), email);
  await tester.enterText(find.byType(TextField).at(1), password);
  await tester.tap(find.widgetWithText(ElevatedButton, 'Sign in'));
  await tester.pumpAndSettle();
}

Future<void> closeApp(WidgetTester tester) async {
  await tester.pumpWidget(const SizedBox());
}

void main() {
  testWidgets(
    'wrong credentials show the error banner and stay on the sign-in page',
    (tester) async {
      await openApp(tester);

      await signIn(tester, 'yuri.sigma@example.com', 'wrong-password');

      expect(find.textContaining('Invalid email or password'), findsOneWidget);
      expect(find.text('Welcome back'), findsOneWidget);
      await closeApp(tester);
    },
  );

  testWidgets('demo account opens the dashboard with history', (tester) async {
    await openApp(tester);

    await signIn(tester, 'demo@interview.dev', 'demo123');

    expect(find.text('Welcome, Yuri Sigma'), findsOneWidget);
    expect(find.text('Topic mastery'), findsOneWidget);
    expect(find.text('#IS-8921'), findsOneWidget);
    expect(find.text('Resume Interview'), findsOneWidget);
    await closeApp(tester);
  });

  testWidgets('practice summary follows the chosen level and topics', (
    tester,
  ) async {
    await openApp(tester);
    await signIn(tester, 'demo@interview.dev', 'demo123');

    await tester.tap(find.text('Start New Interview'));
    await tester.pumpAndSettle();
    expect(find.text('What should we practice?'), findsOneWidget);
    expect(find.text('2 selected'), findsOneWidget);

    await tester.tap(find.text('Senior').first);
    await tester.tap(find.text('System Design'));
    await tester.pumpAndSettle();

    expect(find.text('3 selected'), findsOneWidget);
    expect(find.text('Senior'), findsNWidgets(2));
    await closeApp(tester);
  });

  testWidgets('interview streams a reply and shows test results', (
    tester,
  ) async {
    await openApp(tester);
    await signIn(tester, 'demo@interview.dev', 'demo123');

    await tester.tap(find.text('Resume Interview'));
    await tester.pumpAndSettle(const Duration(milliseconds: 300));
    expect(find.text('Python Core — Middle'), findsOneWidget);
    expect(find.text('LIVE'), findsOneWidget);

    await tester.enterText(
      find.widgetWithText(TextField, '').last,
      'I would store a list of indices per value.',
    );
    await tester.tap(find.byIcon(Icons.arrow_upward));
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(seconds: 1));
    expect(
      find.textContaining('I would store a list of indices'),
      findsOneWidget,
    );
    expect(find.textContaining('clear explanation'), findsOneWidget);

    await tester.tap(find.text('Run Code'));
    await tester.pump(const Duration(seconds: 1));
    expect(find.text('Execution result: 2 passed, 1 failed'), findsOneWidget);
    expect(find.text('Case 3'), findsOneWidget);
    await closeApp(tester);
  });

  testWidgets('ending the interview opens the assessment report', (
    tester,
  ) async {
    await openApp(tester);
    await signIn(tester, 'demo@interview.dev', 'demo123');
    await tester.tap(find.text('Resume Interview'));
    await tester.pumpAndSettle(const Duration(milliseconds: 300));

    await tester.tap(find.text('End Interview'));
    await tester.pumpAndSettle(const Duration(milliseconds: 300));
    await tester.tap(find.text('End interview'));
    await tester.pumpAndSettle(const Duration(milliseconds: 300));

    expect(find.text('Assessment report'), findsOneWidget);
    expect(find.text('Ready for Middle'), findsOneWidget);
    expect(find.text('7.8'), findsOneWidget);
    expect(find.text('Competency rubric'), findsOneWidget);
    await closeApp(tester);
  });

  testWidgets('admin lands on the question bank and can filter it', (
    tester,
  ) async {
    await openApp(tester);

    await signIn(tester, 'admin@interview.dev', 'admin123');

    expect(find.text('Questions & coding tasks'), findsOneWidget);
    expect(find.text('Edit Coding Task #102'), findsOneWidget);
    expect(find.text('LRU cache with TTL'), findsNothing);

    await tester.enterText(find.byType(TextFormField).first, 'LRU');
    await tester.pumpAndSettle();
    expect(find.text('LRU cache with TTL'), findsOneWidget);
    expect(find.text('find_pairs — Two Sum variant'), findsOneWidget);
    await closeApp(tester);
  });
}
