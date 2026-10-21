import 'package:flutter/material.dart';

import '../models/contracts.dart';
import '../state/app_controller.dart';
import '../theme/app_theme.dart';

class ProfilePage extends StatelessWidget {
  const ProfilePage({
    super.key,
    required this.controller,
    required this.onGenerated,
  });

  final AppController controller;
  final VoidCallback onGenerated;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
          children: [
            Text(
              'Your profile',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 6),
            const Text(
              'Tell us about the face, then see matching styles.',
              style: TextStyle(color: AppTheme.textSecondary, height: 1.4),
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton(
                  onPressed: () => controller.loadDemo(maleDemoProfile),
                  child: const Text('Male example'),
                ),
                OutlinedButton(
                  onPressed: () => controller.loadDemo(femaleDemoProfile),
                  child: const Text('Female example'),
                ),
                TextButton(
                  onPressed: controller.resetProfile,
                  child: const Text('Clear'),
                ),
              ],
            ),
            const SizedBox(height: 22),
            _Section(
              title: 'Measurements',
              child: Column(
                children: [
                  _number(controller, 'face_length_ratio', 'Face length'),
                  _number(controller, 'jaw_width_ratio', 'Jaw width'),
                  _number(controller, 'upper_width_ratio', 'Upper face width'),
                  _number(controller, 'lower_face_ratio', 'Lower face'),
                  _number(controller, 'symmetry', 'Symmetry', last: true),
                ],
              ),
            ),
            const SizedBox(height: 16),
            _Section(
              title: 'Features',
              child: Column(
                children: [
                  _dropdown(controller, 'face_shape', 'Face shape', faceShapes),
                  _dropdown(controller, 'jawline', 'Jawline', jawlines),
                  _dropdown(controller, 'forehead', 'Forehead', foreheads),
                  _dropdown(controller, 'hairline', 'Hairline', hairlines),
                  _dropdown(controller, 'gender', 'Gender', genders, last: true),
                ],
              ),
            ),
            const SizedBox(height: 16),
            _Section(
              title: 'What to suggest',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final category in const ['hair', 'beard', 'grooming'])
                        FilterChip(
                          label: Text(_pretty(category)),
                          selected: controller.categories.contains(category),
                          showCheckmark: false,
                          onSelected: (value) =>
                              controller.toggleCategory(category, value),
                        ),
                    ],
                  ),
                  if (controller.fieldErrors['_categories'] != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      controller.fieldErrors['_categories']!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 20),
            if (controller.submitError != null) ...[
              Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFF6F5),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Text(
                  controller.submitError!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            ],
            FilledButton(
              onPressed: controller.submitting
                  ? null
                  : () async {
                      await controller.generate();
                      if (!context.mounted) return;
                      if (controller.lastResult != null &&
                          controller.submitError == null &&
                          controller.resultsAreCurrent) {
                        onGenerated();
                      }
                    },
              child: Text(
                controller.submitting ? 'Finding looks…' : 'See recommendations',
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _number(
    AppController controller,
    String key,
    String label, {
    bool last = false,
  }) {
    return Padding(
      padding: EdgeInsets.only(bottom: last ? 0 : 12),
      child: TextFormField(
        key: ValueKey('$key-${controller.formRevision}'),
        initialValue: controller.profileText[key],
        decoration: InputDecoration(
          labelText: label,
          errorText: controller.fieldErrors[key],
        ),
        keyboardType: const TextInputType.numberWithOptions(
          decimal: true,
          signed: false,
        ),
        onChanged: (value) => controller.setProfileField(key, value),
      ),
    );
  }

  Widget _dropdown(
    AppController controller,
    String key,
    String label,
    List<String> values, {
    bool last = false,
  }) {
    return Padding(
      padding: EdgeInsets.only(bottom: last ? 0 : 12),
      child: DropdownButtonFormField<String>(
        key: ValueKey('dd-$key-${controller.formRevision}'),
        initialValue: values.contains(controller.profileText[key])
            ? controller.profileText[key]
            : null,
        decoration: InputDecoration(
          labelText: label,
          errorText: controller.fieldErrors[key],
        ),
        items: [
          for (final value in values)
            DropdownMenuItem(value: value, child: Text(_pretty(value))),
        ],
        onChanged: (value) {
          if (value != null) controller.setProfileField(key, value);
        },
      ),
    );
  }

  String _pretty(String value) {
    return value
        .split('_')
        .map((part) => part.isEmpty ? part : '${part[0].toUpperCase()}${part.substring(1)}')
        .join(' ');
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primaryDarkBlue.withValues(alpha: 0.05),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 14),
          child,
        ],
      ),
    );
  }
}
