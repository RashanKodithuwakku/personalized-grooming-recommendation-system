import 'dart:io';

import 'package:flutter/material.dart';

import '../services/component_1_api_service.dart';
import 'analysis_result_screen.dart';

/// Full-screen loading state shown while the image is being sent to the
/// backend for analysis.  Uses initState → _performAnalysis so the request
/// fires exactly once per navigation, with no way for the user to double-tap.
class AnalysisLoadingScreen extends StatefulWidget {
  final File imageFile;

  const AnalysisLoadingScreen({super.key, required this.imageFile});

  @override
  State<AnalysisLoadingScreen> createState() => _AnalysisLoadingScreenState();
}

class _AnalysisLoadingScreenState extends State<AnalysisLoadingScreen> {
  final Component1ApiService _apiService = Component1ApiService();

  @override
  void initState() {
    super.initState();
    _performAnalysis();
  }

  Future<void> _performAnalysis() async {
    final result = await _apiService.analyzeFace(widget.imageFile);

    if (!mounted) return;

    if (result != null && result.isSuccess) {
      // Navigate forward on success
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => AnalysisResultScreen(result: result),
        ),
      );
    } else {
      // Surface the backend's specific reason to the user.
      final reason = (result != null && result.message.isNotEmpty)
          ? result.message
          : 'Failed to analyse facial profile. Please retake the photo.';

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(reason),
          duration: const Duration(seconds: 5),
          behavior: SnackBarBehavior.floating,
        ),
      );
      Navigator.pop(context); // Return to photo upload screen
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 24),
            Text(
              'Analysing Facial Profile…',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'This may take a moment.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}
