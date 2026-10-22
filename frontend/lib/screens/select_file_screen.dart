import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../config/api_config.dart';
import '../models/landmark_file.dart';
import '../navigation.dart';
import '../services/picked_bytes.dart';
import '../theme/groom_colors.dart';
import '../theme/groom_type.dart';
import '../utils/format.dart';
import '../utils/landmark_validation.dart';
import '../widgets/groom_background.dart';
import '../widgets/groom_button.dart';
import '../widgets/step_header.dart';
import 'analyzing_screen.dart';

class SelectFileScreen extends StatefulWidget {
  const SelectFileScreen({super.key});

  @override
  State<SelectFileScreen> createState() => _SelectFileScreenState();
}

class _SelectFileScreenState extends State<SelectFileScreen> {
  late final TextEditingController _server = TextEditingController(text: defaultApiBaseUrl());
  LandmarkFile? _file;
  String? _error;
  bool _picking = false;

  @override
  void dispose() {
    _server.dispose();
    super.dispose();
  }

  Future<void> _pick({required bool jsonOnly}) async {
    setState(() => _picking = true);
    try {
      final result = await FilePicker.platform.pickFiles(
        type: jsonOnly ? FileType.custom : FileType.any,
        allowedExtensions: jsonOnly ? const ['json'] : null,
        withData: true,
        allowMultiple: false,
        dialogTitle: 'Choose a landmark JSON file',
      );
      if (!mounted || result == null || result.files.isEmpty) return;
      await _accept(result.files.single);
    } finally {
      if (mounted) setState(() => _picking = false);
    }
  }

  Future<void> _accept(PlatformFile picked) async {
    final name = picked.name.trim().isEmpty ? 'landmark.json' : picked.name.trim();
    final lower = name.toLowerCase();
    const photos = ['.jpg', '.jpeg', '.png', '.webp', '.heic', '.gif'];
    if (photos.any(lower.endsWith)) {
      setState(() {
        _file = null;
        _error = 'That is a photo. This step needs the .json landmark file, not the picture.';
      });
      return;
    }

    final bytes = picked.bytes ?? await readFileBytes(picked.path);
    if (!mounted) return;
    if (bytes == null) {
      setState(() {
        _file = null;
        _error = 'That file could not be read. Try “Browse every file”.';
      });
      return;
    }

    final problem = validateLandmarkBytes(bytes);
    setState(() {
      if (problem != null) {
        _file = null;
        _error = problem;
      } else {
        _file = LandmarkFile(name: name, bytes: Uint8List.fromList(bytes));
        _error = null;
      }
    });
    if (problem == null) HapticFeedback.selectionClick();
  }

  void _continue() {
    final file = _file;
    final urlError = validateBaseUrl(_server.text);
    if (urlError != null) {
      setState(() => _error = urlError);
      return;
    }
    if (file == null) return;
    Navigator.of(context).push(
      fadeRoute(
        AnalyzingScreen(file: file, baseUrl: _server.text.trim()),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final file = _file;
    return Scaffold(
      backgroundColor: GroomColors.ink,
      body: GroomBackground(
        child: SafeArea(
          child: Column(
            children: [
              const StepHeader(step: '01'),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(24, 18, 24, 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('FACE READING', style: GroomType.eyebrow()),
                      const SizedBox(height: 14),
                      Text(
                        'Bring a\nlandmark file.',
                        style: GroomType.display(48, height: 0.92),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Choose the JSON saved on this device. Downloads is the usual place, and Gallery works too if the file was stored there.',
                        style: GroomType.ui(15, color: GroomColors.mute, height: 1.5),
                      ),
                      const SizedBox(height: 28),
                      _FileCard(file: file, picking: _picking),
                      const SizedBox(height: 16),
                      GroomButton(
                        label: _picking ? 'Opening files…' : 'Choose a JSON file',
                        filled: false,
                        onPressed: _picking ? null : () => _pick(jsonOnly: true),
                      ),
                      const SizedBox(height: 8),
                      Center(
                        child: TextButton(
                          onPressed: _picking ? null : () => _pick(jsonOnly: false),
                          child: Text(
                            'Browse every file',
                            style: GroomType.ui(
                              14,
                              weight: FontWeight.w500,
                              color: GroomColors.champagne,
                            ),
                          ),
                        ),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          _error!,
                          style: GroomType.ui(13, color: GroomColors.blush, height: 1.4),
                        ),
                      ],
                      const SizedBox(height: 20),
                      Text('ANALYSIS SERVER', style: GroomType.eyebrow()),
                      const SizedBox(height: 10),
                      TextField(
                        controller: _server,
                        keyboardType: TextInputType.url,
                        autocorrect: false,
                        style: GroomType.ui(14),
                        scrollPadding: const EdgeInsets.only(bottom: 120),
                        decoration: const InputDecoration(
                          hintText: 'http://10.0.2.2:8000',
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'The emulator reaches your computer at 10.0.2.2. Change this only if the service lives somewhere else.',
                        style: GroomType.ui(13, color: GroomColors.mute, height: 1.45),
                      ),
                    ],
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 8, 24, 18),
                child: GroomButton(
                  label: 'Read this face',
                  onPressed: file == null || _picking ? null : _continue,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FileCard extends StatelessWidget {
  const _FileCard({required this.file, required this.picking});

  final LandmarkFile? file;
  final bool picking;

  @override
  Widget build(BuildContext context) {
    final selected = file != null;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 280),
      curve: Curves.easeOutCubic,
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 22),
      decoration: BoxDecoration(
        color: GroomColors.card.withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: selected ? GroomColors.champagne : GroomColors.line,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: selected ? GroomColors.champagne : GroomColors.line,
              ),
            ),
            child: Icon(
              selected ? Icons.check_rounded : Icons.folder_open_rounded,
              color: selected ? GroomColors.champagne : GroomColors.mute,
              size: 22,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  picking
                      ? 'Looking through files'
                      : selected
                          ? file!.name
                          : 'No file yet',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: GroomType.ui(16, weight: FontWeight.w500),
                ),
                const SizedBox(height: 4),
                Text(
                  selected
                      ? '${formatBytes(file!.bytes.length)}  ·  JSON landmark file'
                      : 'JSON from Downloads, Gallery, or files',
                  style: GroomType.ui(13, color: GroomColors.mute),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
