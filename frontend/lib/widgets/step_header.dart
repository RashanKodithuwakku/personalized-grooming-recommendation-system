import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../theme/groom_colors.dart';
import '../theme/groom_type.dart';

class StepHeader extends StatelessWidget {
  const StepHeader({
    super.key,
    required this.step,
    this.onBack,
  });

  final String step;
  final VoidCallback? onBack;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 4, 20, 0),
      child: Row(
        children: [
          if (onBack != null)
            IconButton(
              onPressed: () {
                HapticFeedback.selectionClick();
                onBack!();
              },
              icon: const Icon(Icons.arrow_back_rounded, color: GroomColors.ivory),
              tooltip: 'Back',
            )
          else
            const SizedBox(width: 16),
          Text('GROOM', style: GroomType.eyebrow()),
          const Spacer(),
          Text(step, style: GroomType.eyebrow()),
        ],
      ),
    );
  }
}
