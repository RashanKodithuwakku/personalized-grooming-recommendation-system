import 'package:flutter/material.dart';

import '../state/app_controller.dart';

class ComparePage extends StatelessWidget {
  const ComparePage({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Mode comparison',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const Text(
              'Sends two live requests with the same profile, categories, preferences, exclusions, top-N, and confidence values. Only ranking mode changes. A rank change is not guaranteed.',
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: controller.comparing ? null : controller.compareModes,
              child: Text(
                controller.comparing ? 'Comparing…' : 'Compare live responses',
              ),
            ),
            if (controller.compareError != null) Text(controller.compareError!),
            if (controller.compareStandard != null ||
                controller.compareAware != null) ...[
              if (_staleServer(controller))
                Card(
                  child: ListTile(
                    title: const Text(
                      'This comparison came from a previous server.',
                    ),
                    subtitle: Text(
                      controller.compareStandard?.baseUrl ??
                          controller.compareAware?.baseUrl ??
                          '',
                    ),
                  ),
                )
              else if (controller.compareStandard != null &&
                  controller.compareAware != null &&
                  !controller.comparisonIsCurrent)
                const Card(
                  child: ListTile(
                    title: Text(
                      'This comparison is for the previously submitted profile.',
                    ),
                  ),
                ),
              LayoutBuilder(
                builder: (context, constraints) {
                  final wide = constraints.maxWidth > 800;
                  final children = [
                    if (controller.compareStandard != null)
                      _pane('Standard', controller.compareStandard!),
                    if (controller.compareAware != null)
                      _pane('Confidence-aware', controller.compareAware!),
                  ];
                  if (wide) {
                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        for (final child in children) Expanded(child: child),
                      ],
                    );
                  }
                  return Column(children: children);
                },
              ),
            ],
          ],
        );
      },
    );
  }

  bool _staleServer(AppController controller) {
    final standardUrl = controller.compareStandard?.baseUrl;
    final awareUrl = controller.compareAware?.baseUrl;
    return (standardUrl != null && standardUrl != controller.api.baseUrl) ||
        (awareUrl != null && awareUrl != controller.api.baseUrl);
  }

  Widget _pane(String title, SubmittedBundle bundle) {
    final response = bundle.response;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
            Text('Policy: ${response.policy.policyName}'),
            Text(
              'Active mode: ${response.policy.activeRankingMode ?? response.rankingMode}',
            ),
            if (response.policy.fallbackApplied)
              const Text('Review: fallback applied'),
            for (final category in response.categoryResults) ...[
              const Divider(),
              Text(
                '${category.category} · ${category.status} · ${category.disposition ?? ''}',
              ),
              for (final item in category.recommendations)
                Text(
                  '#${item.rank} ${item.styleName} (${item.styleId}) '
                  'hybrid ${item.hybridScore} (0–1) · '
                  'rule-based ${item.ruleCompatibilityScore ?? '—'} · '
                  'adjusted rule ${item.confidenceAdjustedRuleScore ?? '—'}'
                  '${category.disposition == 'review_required' ? ' · review required' : ''}',
                ),
            ],
            for (final skipped in response.skippedCategories)
              Text('Skipped ${skipped['category']}: ${skipped['status']}'),
          ],
        ),
      ),
    );
  }
}
