// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../domain/dashboard_data.dart';

class TrendChart extends StatelessWidget {
  const TrendChart({
    super.key,
    required this.points,
    this.minY = 4,
    this.maxY = 10,
  });

  final List<TrendPoint> points;
  final double minY;
  final double maxY;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return CustomPaint(
      painter: _TrendPainter(
        points: points,
        minY: minY,
        maxY: maxY,
        line: c.primary,
        grid: c.border,
        dotFill: c.surface,
        label: c.textFaint,
        font: monoStyle(context, size: 11, color: c.textFaint),
      ),
      size: Size.infinite,
    );
  }
}

class _TrendPainter extends CustomPainter {
  _TrendPainter({
    required this.points,
    required this.minY,
    required this.maxY,
    required this.line,
    required this.grid,
    required this.dotFill,
    required this.label,
    required this.font,
  });

  final List<TrendPoint> points;
  final double minY;
  final double maxY;
  final Color line;
  final Color grid;
  final Color dotFill;
  final Color label;
  final TextStyle font;

  static const _left = 34.0;
  static const _bottom = 26.0;

  @override
  void paint(Canvas canvas, Size size) {
    if (points.length < 2) return;
    final plot = Rect.fromLTRB(_left, 8, size.width - 8, size.height - _bottom);
    final gridPaint = Paint()
      ..color = grid
      ..strokeWidth = 1;
    for (var y = minY; y <= maxY; y += 2) {
      final dy = _y(y, plot);
      canvas.drawLine(Offset(plot.left, dy), Offset(plot.right, dy), gridPaint);
      _text(canvas, y.toStringAsFixed(0), Offset(0, dy - 7), font);
    }
    final offsets = [
      for (var i = 0; i < points.length; i++)
        Offset(
          plot.left +
              plot.width * i / (points.length - 1) * 0.96 +
              plot.width * 0.02,
          _y(points[i].score, plot),
        ),
    ];
    final path = Path()..moveTo(offsets.first.dx, offsets.first.dy);
    for (var i = 0; i < offsets.length - 1; i++) {
      final p0 = i == 0 ? offsets[i] : offsets[i - 1];
      final p1 = offsets[i];
      final p2 = offsets[i + 1];
      final p3 = i + 2 < offsets.length ? offsets[i + 2] : p2;
      path.cubicTo(
        p1.dx + (p2.dx - p0.dx) / 6,
        p1.dy + (p2.dy - p0.dy) / 6,
        p2.dx - (p3.dx - p1.dx) / 6,
        p2.dy - (p3.dy - p1.dy) / 6,
        p2.dx,
        p2.dy,
      );
    }
    canvas.drawPath(
      path,
      Paint()
        ..color = line
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.4
        ..strokeCap = StrokeCap.round,
    );
    for (var i = 0; i < offsets.length; i++) {
      final isEdge = i == 0;
      if (isEdge && points.length > 2) {
        canvas.drawCircle(offsets[i], 4, Paint()..color = line);
      }
      if (i > 0 || points.length <= 2) {
        canvas.drawCircle(offsets[i], 4.2, Paint()..color = dotFill);
        canvas.drawCircle(
          offsets[i],
          4.2,
          Paint()
            ..color = line
            ..style = PaintingStyle.stroke
            ..strokeWidth = 2,
        );
      }
      _label(canvas, points[i].label, offsets[i].dx, size);
    }
  }

  double _y(double v, Rect plot) =>
      plot.bottom - (v - minY) / (maxY - minY) * plot.height;

  void _label(Canvas canvas, String text, double centerX, Size size) {
    final painter = TextPainter(
      text: TextSpan(text: text, style: font),
      textDirection: TextDirection.ltr,
    )..layout();
    final x = (centerX - painter.width / 2).clamp(
      0.0,
      size.width - painter.width,
    );
    painter.paint(canvas, Offset(x, size.height - 16));
  }

  void _text(Canvas canvas, String text, Offset at, TextStyle style) {
    final painter = TextPainter(
      text: TextSpan(text: text, style: style),
      textDirection: TextDirection.ltr,
    )..layout();
    painter.paint(canvas, at);
  }

  @override
  bool shouldRepaint(_TrendPainter old) =>
      old.points != points || old.line != line || old.grid != grid;
}
