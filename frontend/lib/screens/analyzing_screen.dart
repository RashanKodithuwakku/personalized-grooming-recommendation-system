import 'dart:async';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../models/landmark_file.dart';
import '../navigation.dart';
import '../services/analysis_service.dart';
import '../theme/groom_colors.dart';
import '../theme/groom_type.dart';
import '../widgets/groom_background.dart';
import '../widgets/groom_button.dart';
import '../widgets/reading_mark.dart';
import '../widgets/step_header.dart';
import 'face_type_screen.dart';

class AnalyzingScreen extends StatefulWidget {
  const AnalyzingScreen({
    super.key,
    required this.file,
    required this.baseUrl,
    this.client,
    this.minimumVisible = const Duration(milliseconds: 1500),
  });

  final LandmarkFile file;
  final String baseUrl;
  final http.Client? client;
  final Duration minimumVisible;

  @override
  State<AnalyzingScreen> createState() => _AnalyzingScreenState();
}

class _AnalyzingScreenState extends State<AnalyzingScreen> {
  static const _lines = [
    'Placing the landmarks',
    'Comparing the six face shapes',
    'Checking the left and right sides',
    'Measuring the upper, middle, and lower face',
  ];

  late final http.Client _client = widget.client ?? http.Client();
  late final bool _ownsClient = widget.client == null;
  late final AnalysisService _service = AnalysisService(client: _client);

  int _line = 0;
  String? _error;
  bool _busy = true;
  Timer? _lineTimer;

  @override
  void initState() {
    super.initState();
    _scheduleLine();
    _start();
  }

  void _scheduleLine() {
    _lineTimer?.cancel();
    _lineTimer = Timer(const Duration(milliseconds: 1600), () {
      if (!mounted || !_busy || _error != null) return;
      setState(() => _line = (_line + 1) % _lines.length);
      _scheduleLine();
    });
  }

  void _stopLines() {
    _lineTimer?.cancel();
    _lineTimer = null;
  }

  Future<void> _start() async {
    if (_error != null || !_busy) {
      setState(() {
        _error = null;
        _busy = true;
      });
    }
    _scheduleLine();
    final started = DateTime.now();
    try {
      final profile = await _service.analyse(
        endpoint: profileUri(widget.baseUrl),
        bytes: widget.file.bytes,
      );
      final remain = widget.minimumVisible - DateTime.now().difference(started);
      if (remain > Duration.zero) {
        await Future<void>.delayed(remain);
      }
      if (!mounted) return;
      _stopLines();
      setState(() => _busy = false);
      Navigator.of(context).pushReplacement(
        fadeRoute(
          FaceTypeScreen(profile: profile, fileName: widget.file.name),
        ),
      );
    } on AnalysisException catch (error) {
      _showError(error.message);
    } on FormatException catch (error) {
      _showError(error.message);
    } catch (_) {
      _showError('The reading stopped before it could finish.');
    }
  }

  void _showError(String message) {
    if (!mounted) return;
    _stopLines();
    setState(() {
      _busy = false;
      _error = message;
    });
  }

  @override
  void dispose() {
    _stopLines();
    if (_ownsClient) _client.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final error = _error;
    return Scaffold(
      backgroundColor: GroomColors.ink,
      body: GroomBackground(
        child: SafeArea(
          child: Column(
            children: [
              StepHeader(
                step: '··',
                onBack: () => Navigator.of(context).maybePop(),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 28),
                  child: Column(
                    children: [
                      const Spacer(flex: 3),
                      ReadingMark(spinning: error == null),
                      const SizedBox(height: 36),
                      Text(
                        error == null ? 'Reading the landmarks' : 'The reading paused',
                        textAlign: TextAlign.center,
                        style: GroomType.display(36),
                      ),
                      const SizedBox(height: 14),
                      AnimatedSwitcher(
                        duration: const Duration(milliseconds: 360),
                        child: Text(
                          error ?? _lines[_line],
                          key: ValueKey(error ?? _line),
                          textAlign: TextAlign.center,
                          style: GroomType.ui(
                            15,
                            color: error == null ? GroomColors.mute : GroomColors.blush,
                            height: 1.5,
                          ),
                        ),
                      ),
                      const SizedBox(height: 22),
                      Text(
                        widget.file.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: GroomType.ui(13, color: GroomColors.champagne, letterSpacing: 0.3),
                      ),
                      const Spacer(flex: 4),
                      if (error != null) ...[
                        GroomButton(label: 'Try again', onPressed: _start),
                        const SizedBox(height: 10),
                        GroomButton(
                          label: 'Choose another file',
                          filled: false,
                          onPressed: () => Navigator.of(context).maybePop(),
                        ),
                        const SizedBox(height: 12),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
