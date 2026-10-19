import 'package:flutter/material.dart';
import '../models/analysis_result.dart';
import '../widgets/result_profile_card.dart';

class AnalysisResultScreen extends StatelessWidget {
  final AnalysisResult result;

  const AnalysisResultScreen({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Analysis Results'),
        centerTitle: true,
        automaticallyImplyLeading: false,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(
                Icons.check_circle_outline,
                size: 64,
                color: Colors.green,
              ),
              const SizedBox(height: 16),
              Text(
                'Facial Profile Complete',
                style: theme.textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                'Here are your AI-predicted hairline and jawline traits.',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[600],
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              ResultProfileCard(
                title: 'Hairline Type',
                resultValue: result.hairlineResult.isEmpty
                    ? 'N/A'
                    : result.hairlineResult,
                confidence: result.hairlineConfidence,
                icon: Icons.face_retouching_natural,
              ),
              const SizedBox(height: 20),
              ResultProfileCard(
                title: 'Jawline Shape',
                resultValue: result.jawlineResult.isEmpty
                    ? 'N/A'
                    : result.jawlineResult,
                confidence: result.jawlineConfidence,
                icon: Icons.portrait,
              ),
              const SizedBox(height: 40),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () {
                        // Pop back to the initial photo upload screen to retake photo
                        Navigator.popUntil(context, (route) => route.isFirst);
                      },
                      icon: const Icon(Icons.refresh),
                      label: const Text('Retake Photo'),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () {
                        // Return to root screen or finish flow
                        Navigator.popUntil(context, (route) => route.isFirst);
                      },
                      icon: const Icon(Icons.check),
                      label: const Text('Done'),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

