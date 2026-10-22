import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/groom_colors.dart';

/// A quiet diagram of a face: oval, center line, and a moving arc.
class ReadingMark extends StatefulWidget {
  const ReadingMark({super.key, this.size = 148, this.spinning = true});

  final double size;
  final bool spinning;

  @override
  State<ReadingMark> createState() => _ReadingMarkState();
}

class _ReadingMarkState extends State<ReadingMark> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2400),
  );

  @override
  void initState() {
    super.initState();
    if (widget.spinning) _controller.repeat();
  }

  @override
  void didUpdateWidget(ReadingMark oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.spinning && !_controller.isAnimating) {
      _controller.repeat();
    } else if (!widget.spinning && _controller.isAnimating) {
      _controller.stop();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: widget.size,
      height: widget.size,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          return CustomPaint(
            painter: _MarkPainter(turn: _controller.value, spinning: widget.spinning),
          );
        },
      ),
    );
  }
}

class _MarkPainter extends CustomPainter {
  _MarkPainter({required this.turn, required this.spinning});

  final double turn;
  final bool spinning;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;
    final hairline = Paint()
      ..color = GroomColors.champagne.withValues(alpha: 0.35)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    canvas.drawCircle(center, radius - 1, hairline);
    canvas.drawOval(
      Rect.fromCenter(
        center: center,
        width: radius * 1.05,
        height: radius * 1.55,
      ),
      hairline,
    );
    canvas.drawLine(
      Offset(center.dx, center.dy - radius * 0.62),
      Offset(center.dx, center.dy + radius * 0.62),
      hairline,
    );
    canvas.drawLine(
      Offset(center.dx - radius * 0.28, center.dy - radius * 0.08),
      Offset(center.dx + radius * 0.28, center.dy - radius * 0.08),
      hairline,
    );

    final arc = Paint()
      ..color = GroomColors.champagne
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.6
      ..strokeCap = StrokeCap.round;
    final sweep = spinning ? math.pi * 1.15 : math.pi * 1.7;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius - 8),
      turn * math.pi * 2,
      sweep,
      false,
      arc,
    );
  }

  @override
  bool shouldRepaint(_MarkPainter oldDelegate) => oldDelegate.turn != turn;
}
