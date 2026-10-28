// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';

class Topic {
  const Topic({
    required this.id,
    required this.title,
    required this.description,
    required this.icon,
  });

  final int id;
  final String title;
  final String description;
  final IconData icon;
}

const practiceTopics = [
  Topic(
    id: 1,
    title: 'Python Core',
    description: 'Data model, functions, iterators, typing',
    icon: Icons.data_object,
  ),
  Topic(
    id: 2,
    title: 'Algorithms',
    description: 'Complexity, search, sorting, dynamic programming',
    icon: Icons.account_tree_outlined,
  ),
  Topic(
    id: 3,
    title: 'Data Structures',
    description: 'Arrays, maps, trees, graphs, queues',
    icon: Icons.hub_outlined,
  ),
  Topic(
    id: 4,
    title: 'SQL & Databases',
    description: 'Queries, indexes, transactions, modeling',
    icon: Icons.storage_outlined,
  ),
  Topic(
    id: 5,
    title: 'System Design',
    description: 'APIs, scaling, reliability, trade-offs',
    icon: Icons.device_hub,
  ),
  Topic(
    id: 6,
    title: 'Testing & Debugging',
    description: 'Unit tests, diagnosis, observability',
    icon: Icons.bug_report_outlined,
  ),
];
