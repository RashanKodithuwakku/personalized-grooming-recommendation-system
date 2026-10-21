import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../state/app_controller.dart';

class SystemPage extends StatelessWidget {
  const SystemPage({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final models = (controller.modelsInfo?['models'] as List?) ?? const [];
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'System information',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const Text(
              'Metadata below comes from the live API. It does not replace a recommendation request.',
            ),
            Text('Base URL: ${controller.api.baseUrl}'),
            Text(
              'Connection: ${_connectionLabel(controller.connectionStatus)}',
            ),
            if (controller.connectionError != null)
              Text(controller.connectionError!),
            if (!controller.metadataCurrent)
              const Text(
                'Model metadata for the current server is not available.',
              ),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: controller.checking
                  ? null
                  : controller.refreshConnection,
              child: const Text('Retry connection'),
            ),
            const SizedBox(height: 12),
            if (controller.metadataCurrent)
              for (final model in models)
                ListTile(
                  title: Text((model as Map)['filename']?.toString() ?? '—'),
                  isThreeLine: true,
                  subtitle: Text(
                    'Loaded: ${model['loaded'] ?? '—'} · role: ${model['role'] ?? '—'} · '
                    'features: ${(model['feature_names'] as List?)?.length ?? 0}\n'
                    'SHA256: ${model['sha256'] ?? 'Not available'}',
                  ),
                ),
            if (controller.metadataCurrent && controller.capabilities != null)
              Text(
                'Rules available: ${controller.capabilities!['rules_available']}',
              ),
            if (controller.metadataCurrent &&
                controller.capabilities?['ranking_policy'] != null)
              Text(
                'Default policy: ${controller.capabilities!['ranking_policy']['policy_name']}',
              ),
            if (controller.lastResult != null)
              Text('Last request server: ${controller.lastResult!.baseUrl}'),
            ExpansionTile(
              title: const Text('Last request JSON'),
              children: [_jsonBlock(controller.lastResult?.request)],
            ),
            ExpansionTile(
              title: const Text('Last response JSON'),
              children: [_jsonBlock(controller.lastResult?.response.raw)],
            ),
          ],
        );
      },
    );
  }

  String _connectionLabel(String status) {
    switch (status) {
      case 'ready':
        return 'Ready';
      case 'notReady':
        return 'Reachable, not ready';
      case 'checking':
        return 'Checking';
      default:
        return 'Unreachable';
    }
  }

  Widget _jsonBlock(Object? value) {
    final text = value == null
        ? 'No request yet.'
        : const JsonEncoder.withIndent('  ').convert(value);
    return Align(
      alignment: Alignment.centerLeft,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextButton(
            onPressed: () => Clipboard.setData(ClipboardData(text: text)),
            child: const Text('Copy'),
          ),
          SelectableText(text),
        ],
      ),
    );
  }
}
