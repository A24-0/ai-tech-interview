// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

enum Level {
  junior(
    'Junior',
    'Foundational syntax and guided problem solving.',
    '0–2 years experience',
  ),
  middle(
    'Middle',
    'Independent reasoning and production trade-offs.',
    '2–5 years experience',
  ),
  senior(
    'Senior',
    'Architecture, leadership, and deep technical judgment.',
    '5+ years experience',
  );

  const Level(this.label, this.description, this.experience);

  final String label;
  final String description;
  final String experience;

  String get apiValue => name;
}
