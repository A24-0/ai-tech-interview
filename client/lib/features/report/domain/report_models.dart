// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';

enum FindingTone { positive, warning }

class Finding {
  const Finding({required this.tone, required this.title, required this.text});

  final FindingTone tone;
  final String title;
  final String text;
}

class RubricScore {
  const RubricScore({
    required this.name,
    required this.icon,
    required this.score,
    required this.note,
  });

  final String name;
  final IconData icon;
  final double score;
  final String note;
}

class CodingReview {
  const CodingReview({
    required this.language,
    required this.passed,
    required this.total,
    required this.code,
    required this.complexity,
    required this.findings,
    required this.timeMs,
    required this.memoryMb,
    required this.percentile,
  });

  final String language;
  final int passed;
  final int total;
  final String code;
  final String complexity;
  final List<Finding> findings;
  final int timeMs;
  final double memoryMb;
  final int percentile;
}

class TheoryReview {
  const TheoryReview({
    required this.question,
    required this.answer,
    required this.findings,
    required this.score,
  });

  final String question;
  final String answer;
  final List<Finding> findings;
  final double score;
}

class AssessmentReport {
  const AssessmentReport({
    required this.id,
    required this.track,
    required this.date,
    required this.durationMinutes,
    required this.format,
    required this.score,
    required this.verdictTitle,
    required this.verdictText,
    required this.rubric,
    required this.coding,
    required this.theory,
    required this.prompts,
  });

  final String id;
  final String track;
  final String date;
  final int durationMinutes;
  final String format;
  final double score;
  final String verdictTitle;
  final String verdictText;
  final List<RubricScore> rubric;
  final CodingReview coding;
  final TheoryReview theory;
  final int prompts;
}
