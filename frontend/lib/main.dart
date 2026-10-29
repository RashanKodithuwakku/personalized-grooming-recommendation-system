
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

void main() => runApp(MyApp());

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) =>
      MaterialApp(
        debugShowCheckedModeBanner: false,
        home: PreviewScreen(),
      );
}

class PreviewScreen extends StatefulWidget {
  @override
  State<PreviewScreen> createState() => _PreviewScreenState();
}

class _PreviewScreenState extends State<PreviewScreen> {
  // Backend API address
  static const String apiBase = 'http://127.0.0.1:8000';

  // Flutter Web compatible image storage
  Uint8List? _image;
  String? _imageName;

  String? _explanation;
  String? _previewPath;
  String? _advancedPreviewPath;
  Map<String, dynamic>? _alignmentResult;
  bool _isAlignmentLoading = false;
  String? currentStyle;
  String? currentVariant;

  int currentRank = 1;
  String selectedGender = 'male';
  String selectedStyleType = 'hairstyle';

  bool _isLoading = false;
  bool _isAdvancedLoading = false;
  int _previewCacheVersion = 0;

  Future<void> pickImage() async {
    try {
      final picked = await ImagePicker().pickImage(
        source: ImageSource.gallery,
      );

      if (picked == null) return;

      final imageBytes = await picked.readAsBytes();

      if (!mounted) return;

      setState(() {
        _image = imageBytes;
        _imageName = picked.name;
        currentRank = 1;
        _advancedPreviewPath = null;
        _previewPath = null;
        _explanation = null;
        currentStyle = null;
        currentVariant = null;
      });

      await uploadAndGetPreview();
    } catch (e) {
      _showMessage('Could not select photo: $e');
    }
  }

  Future<void> uploadAndGetPreview() async {
    if (_image == null) return;

    setState(() => _isLoading = true);

    try {
      final uri = Uri.parse(
        '$apiBase/generate-preview'
        '?gender=$selectedGender'
        '&style_type=$selectedStyleType'
        '&current_rank=$currentRank',
      );

      final request = http.MultipartRequest('POST', uri)
        ..files.add(
          http.MultipartFile.fromBytes(
            'file',
            _image!,
            filename: _imageName ?? 'photo.jpg',
          ),
        );

      final response = await request.send();
      final body = await response.stream.bytesToString();
      final data = jsonDecode(body);

      if (response.statusCode < 200 ||
          response.statusCode >= 300) {
        throw Exception(
          data is Map
              ? data['detail'] ?? data['error'] ?? body
              : body,
        );
      }

      if (data is! Map<String, dynamic>) {
        throw Exception('Unexpected preview response.');
      }

      if (data.containsKey('error')) {
        throw Exception(data['error']);
      }

      if (!mounted) return;

      setState(() {
        _explanation = data['explanation']?.toString();
        _previewPath = data['preview_path']?.toString();
        currentStyle = data['style']?.toString();
        currentVariant = data['variant']?.toString();
        _advancedPreviewPath = null;
        _previewCacheVersion++;
      });
    } catch (e) {
      _showMessage('Preview failed: $e');
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void switchStyleType(String newType) {
    setState(() {
      selectedStyleType = newType;
      currentRank = 1;
      _advancedPreviewPath = null;
      _previewPath = null;
      _explanation = null;
      currentStyle = null;
      currentVariant = null;
    });

    if (_image != null) {
      uploadAndGetPreview();
    }
  }

  Future<void> sendFeedback(String value) async {
    if (_image == null ||
        currentStyle == null ||
        currentVariant == null) {
      _showMessage('Generate a preview before submitting feedback.');
      return;
    }

    try {
      final response = await http.post(
        Uri.parse('$apiBase/feedback'),
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'user_id': 'test_user',
          'current_rank': currentRank,
          'feedback_value': value,
          'style_shown': currentStyle,
          'variant_shown': currentVariant,
          'gender': selectedGender,
          'style_type': selectedStyleType,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode < 200 ||
          response.statusCode >= 300) {
        throw Exception(
          data is Map
              ? data['detail'] ?? response.body
              : response.body,
        );
      }

      if (value == 'dislike') {
        setState(() {
          currentRank++;
          _advancedPreviewPath = null;
          _previewPath = null;
          _explanation = null;
        });

        await uploadAndGetPreview();
      } else if (value == 'like') {
        if (selectedStyleType != 'hairstyle') {
          _showMessage(
            'HairFastGAN advanced preview supports hairstyles only.',
          );
          return;
        }

        showAdvancedPreviewPopup();
      }
    } catch (e) {
      _showMessage('Feedback failed: $e');
    }
  }

  void showAdvancedPreviewPopup() {
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Want an advanced preview?'),
        content: const Text(
          'Would you like to generate a more realistic hairstyle '
          'preview using HairFastGAN?',
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(dialogContext);
              sendAdvancedPreviewChoice(false);
            },
            child: const Text('No, keep current'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(dialogContext);
              sendAdvancedPreviewChoice(true);
            },
            child: const Text('Yes, show advanced'),
          ),
        ],
      ),
    );
  }

  Future<void> sendAdvancedPreviewChoice(
    bool wantsAdvanced,
  ) async {
    try {
      final choiceResponse = await http.post(
        Uri.parse('$apiBase/advanced-preview-choice'),
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'wants_advanced': wantsAdvanced,
        }),
      );

      final choiceData = jsonDecode(choiceResponse.body);

      if (choiceResponse.statusCode < 200 ||
          choiceResponse.statusCode >= 300) {
        throw Exception(
          choiceData is Map
              ? choiceData['detail'] ?? choiceResponse.body
              : choiceResponse.body,
        );
      }

      if (!wantsAdvanced) {
        _showMessage(
          choiceData['message']?.toString() ??
              'Keeping current preview.',
        );
        return;
      }

      await generateAdvancedPreview();
    } catch (e) {
      _showMessage('Advanced preview unavailable: $e');
    }
  }

  Future<void> generateAdvancedPreview() async {
    if (_image == null) {
      _showMessage('Upload a photo first.');
      return;
    }

    if (selectedStyleType != 'hairstyle') {
      _showMessage(
        'HairFastGAN advanced preview supports hairstyles only.',
      );
      return;
    }

    setState(() => _isAdvancedLoading = true);

    try {
      final styleName =
          currentVariant ?? currentStyle ?? 'selected_style';

      final uri = Uri.parse(
        '$apiBase/advanced-preview'
        '?gender=$selectedGender'
        '&style_name=${Uri.encodeQueryComponent(styleName)}',
      );

      // Use bytes instead of File.path for Flutter Web.
      final request = http.MultipartRequest('POST', uri)
        ..files.add(
          http.MultipartFile.fromBytes(
            'file',
            _image!,
            filename: _imageName ?? 'photo.jpg',
          ),
        );

      final response = await request.send();
      final body = await response.stream.bytesToString();
      final data = jsonDecode(body);

      if (response.statusCode < 200 ||
          response.statusCode >= 300) {
        throw Exception(
          data is Map ? data['detail'] ?? body : body,
        );
      }

      if (data is! Map<String, dynamic> ||
          data['preview_path'] == null) {
        throw Exception(
          'HairFastGAN returned no preview path.',
        );
      }

      if (!mounted) return;

      setState(() {
        _advancedPreviewPath =
            data['preview_path'].toString();
      });

      _showMessage('Advanced preview generated.');
    } catch (e) {
      _showMessage('HairFastGAN failed: $e');
    } finally {
      if (mounted) {
        setState(() => _isAdvancedLoading = false);
      }
    }
  }


  Future<void> runAlignmentComparison() async {
    if (_image == null) {
      _showMessage('Upload a photo first.');
      return;
    }

    setState(() => _isAlignmentLoading = true);
    try {
      final uri = Uri.parse(
        '$apiBase/alignment-metrics'
        '?gender=$selectedGender',
      );

      final request = http.MultipartRequest('POST', uri)
        ..files.add(
          http.MultipartFile.fromBytes(
            'file',
            _image!,
            filename: _imageName ?? 'photo.jpg',
          ),
        );

      final response = await request.send();
      final body = await response.stream.bytesToString();
      final decoded = jsonDecode(body);

      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception(
          decoded is Map ? decoded['detail'] ?? decoded['error'] ?? body : body,
        );
      }
      if (decoded is! Map<String, dynamic>) {
        throw Exception('Unexpected alignment-metrics response.');
      }
      if (!mounted) return;
      setState(() {
        _alignmentResult = decoded;
        _previewCacheVersion++;
      });
    } catch (e) {
      _showMessage('Alignment comparison failed: $e');
    } finally {
      if (mounted) setState(() => _isAlignmentLoading = false);
    }
  }

  Widget _metricRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: Color(0xFF7D8490), fontSize: 13),
            ),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: const TextStyle(
                color: Color(0xFF20232A),
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _comparisonMetric(String title, String value, String caption,
      {Color valueColor = const Color(0xFF20232A)}) {
    return Expanded(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(color: Color(0xFF7D8490), fontSize: 13)),
            const SizedBox(height: 8),
            Text(value, style: TextStyle(fontSize: 27, fontWeight: FontWeight.w800, color: valueColor)),
            const SizedBox(height: 4),
            Text(caption, style: const TextStyle(color: Color(0xFF7D8490), fontSize: 12)),
          ],
        ),
      ),
    );
  }

  Widget _alignmentEvaluationSummary(Map result) {
    final metrics = result['accuracy_metrics'] is Map
        ? result['accuracy_metrics'] as Map
        : const {};
    final baselineRaw = metrics['baseline_mean_nme_percent'];
    final affineRaw = metrics['affine_mean_nme_percent'];
    final reductionRaw = metrics['error_reduction_percent'];

    // Display backend-calculated values only; never substitute demo placeholders.
    final isDraft = baselineRaw == null || affineRaw == null;
    final baseline = baselineRaw is num ? baselineRaw.toDouble() : null;
    final affine = affineRaw is num ? affineRaw.toDouble() : null;
    final reduction = reductionRaw is num ? reductionRaw.toDouble() : null;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF111111),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Alignment Evaluation Results',
            style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 18),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _comparisonMetric(
                'Fixed overlay baseline',
                '${baseline?.toStringAsFixed(2) ?? 'N/A'}%',
                'Mean NME error',
                valueColor: Colors.white,
              ),
              _comparisonMetric(
                'Affine alignment',
                '${affine?.toStringAsFixed(2) ?? 'N/A'}%',
                'Mean NME error',
                valueColor: const Color(0xFF35D07F),
              ),
            ],
          ),
          const Divider(color: Color(0xFF383838), height: 28),
          Row(
            children: [
              const Expanded(
                child: Text(
                  'Error reduction',
                  style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w800),
                ),
              ),
              Text(
                '${reduction?.toStringAsFixed(2) ?? 'N/A'}%',
                style: const TextStyle(color: Color(0xFF35D07F), fontSize: 22, fontWeight: FontWeight.w800),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            isDraft
                ? 'Backend did not return complete calculated metrics. Please check the fixed reference JSON and backend logs.'
                : 'Calculated from the fixed reference JSON using the NME formula. Lower NME error is better.',
            style: TextStyle(
              color: isDraft ? const Color(0xFFFFD166) : const Color(0xFFB8B8B8),
              fontSize: 12,
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }

  Widget _alignmentComparisonCard() {
    final result = _alignmentResult;
    if (result == null) return const SizedBox.shrink();
    final metrics = result['accuracy_metrics'] is Map
        ? result['accuracy_metrics'] as Map
        : const {};
    final formulas = result['formulas'] is Map
        ? result['formulas'] as Map
        : const {};
    final baselineRaw = metrics['baseline_mean_nme_percent'];
    final affineRaw = metrics['affine_mean_nme_percent'];
    final reductionRaw = metrics['error_reduction_percent'];

    return _sectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Fixed User Landmark Alignment Evaluation',
              style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
          const SizedBox(height: 5),
          const Text(
            'This panel always uses the saved reference-user landmarks. Uploading another photo does not change these calculation inputs.',
            style: TextStyle(color: Color(0xFF7D8490), fontSize: 13, height: 1.4),
          ),
          const SizedBox(height: 14),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(color: const Color(0xFF111111), borderRadius: BorderRadius.circular(16)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Alignment Evaluation Results', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800)),
              const SizedBox(height: 18),
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                _comparisonMetric('Fixed overlay baseline', baselineRaw is num ? '${baselineRaw.toStringAsFixed(2)}%' : 'N/A', 'Mean NME error', valueColor: Colors.white),
                _comparisonMetric('Affine alignment', affineRaw is num ? '${affineRaw.toStringAsFixed(2)}%' : 'N/A', 'Mean NME error', valueColor: const Color(0xFF35D07F)),
              ]),
              const Divider(color: Color(0xFF383838), height: 28),
              Row(children: [
                const Expanded(child: Text('Error reduction', style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w800))),
                Text(reductionRaw is num ? '${reductionRaw.toStringAsFixed(2)}%' : 'N/A', style: const TextStyle(color: Color(0xFF35D07F), fontSize: 22, fontWeight: FontWeight.w800)),
              ]),
              const SizedBox(height: 10),
              const Text('Lower NME means a smaller landmark displacement relative to the normalizer.', style: TextStyle(color: Color(0xFFB8B8B8), fontSize: 12, height: 1.45)),
            ]),
          ),
          const SizedBox(height: 16),
          const Text('Formula used', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
          const SizedBox(height: 7),
          _metricRow('NME', formulas['nme']?.toString() ?? 'NME (%) = (mean landmark distance / normalizer) × 100'),
          _metricRow('Error reduction', formulas['error_reduction']?.toString() ?? '((baseline NME − affine NME) / baseline NME) × 100'),
          _metricRow('Reference user', '${result['reference_id'] ?? 'fixed reference'}'),
          _metricRow('Selected template', '${result['selected_template'] ?? 'N/A'}'),
          _metricRow('Normalizer', '${result['normalizer_px'] ?? 'N/A'} px (jaw landmark distance)'),
          if (result['user_landmarks'] is List)
            _metricRow('Fixed user landmarks', (result['user_landmarks'] as List).map((p) => '(${(p as List)[0]}, ${p[1]})').join('  ')),
          if (result['accuracy_note'] != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(11),
              decoration: BoxDecoration(color: const Color(0xFFFFF4DB), borderRadius: BorderRadius.circular(12)),
              child: Text(result['accuracy_note'].toString(), style: const TextStyle(fontSize: 12, height: 1.4, color: Color(0xFF76561B))),
            ),
          ],
        ],
      ),
    );
  }

  void _showMessage(String message) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 5),
      ),
    );
  }

  String? _imageUrl(String? path) {
    if (path == null || path.isEmpty) return null;
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path;
    }
    final separator = path.contains('?') ? '&' : '?';
    return '$apiBase$path${separator}v=$_previewCacheVersion';
  }

  Widget _genderButton(String label, String value) {
    final selected = selectedGender == value;
    return Expanded(
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () {
          if (selectedGender == value) return;
          setState(() {
            selectedGender = value;
            currentRank = 1;
            _advancedPreviewPath = null;
          });
          if (_image != null) uploadAndGetPreview();
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          padding: const EdgeInsets.symmetric(vertical: 11),
          decoration: BoxDecoration(
            color: selected ? const Color(0xFFDDEFEF) : const Color(0xFFF0F1F4),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: selected ? const Color(0xFFB9DEDA) : const Color(0xFFE2E5E9),
            ),
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                color: selected ? const Color(0xFF176E68) : const Color(0xFF656C77),
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _sectionCard({required Widget child}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: const Color(0xFFE2E5E9)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.025),
            blurRadius: 14,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: child,
    );
  }

  Widget _styleTab(String label, String value) {
    final selected = selectedStyleType == value;
    final enabled = value != 'beard' || selectedGender == 'male';
    return Expanded(
      child: InkWell(
        borderRadius: BorderRadius.circular(17),
        onTap: !enabled || _isLoading
            ? null
            : () {
                if (selectedStyleType == value) return;
                switchStyleType(value);
              },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 14),
          decoration: BoxDecoration(
            color: selected ? Colors.white : const Color(0xFFE8EAEE),
            borderRadius: BorderRadius.circular(17),
            boxShadow: selected
                ? [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.08),
                      blurRadius: 5,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : [],
          ),
          child: Center(
            child: Text(
              label,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: !enabled
                    ? const Color(0xFFB0B4BC)
                    : selected
                        ? const Color(0xFF176E68)
                        : const Color(0xFF777E89),
                fontSize: 14,
                fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
              ),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final normalUrl = _imageUrl(_previewPath);
    final advancedUrl = _imageUrl(_advancedPreviewPath);

    return Scaffold(
      backgroundColor: const Color(0xFFF5F6F8),
      appBar: AppBar(
        backgroundColor: const Color(0xFFF5F6F8),
        foregroundColor: const Color(0xFF171A20),
        elevation: 0,
        toolbarHeight: 94,
        titleSpacing: 20,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Style Recommendations',
              style: TextStyle(
                fontSize: 23,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: 7),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
                  decoration: BoxDecoration(
                    color: const Color(0xFFDDEFEF),
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: Text(
                    selectedGender == 'male' ? 'Male' : 'Female',
                    style: const TextStyle(
                      color: Color(0xFF176E68),
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(width: 9),
                const Icon(Icons.thumb_up_alt_outlined, size: 16, color: Color(0xFF238C83)),
                const SizedBox(width: 5),
                const Flexible(
                  child: Text(
                    'Personalized for you',
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: Color(0xFF7D8490),
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.all(5),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE8EAEE),
                      borderRadius: BorderRadius.circular(22),
                    ),
                    child: Row(
                      children: [
                        _styleTab('💇 Hairstyles', 'hairstyle'),
                        const SizedBox(width: 5),
                        _styleTab('🧔 Beard Styles', 'beard'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 22),
                  Row(
                    children: [
                      const Expanded(
                        child: Text(
                          'Your style preview',
                          style: TextStyle(
                            color: Color(0xFF20232A),
                            fontSize: 19,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFFDDEFEF),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          '#$currentRank',
                          style: const TextStyle(
                            color: Color(0xFF176E68),
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  _sectionCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'GET STARTED',
                          style: TextStyle(
                            color: Color(0xFF7D8490),
                            fontSize: 11,
                            letterSpacing: 1.2,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 7),
                        const Text(
                          'Upload your photo',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                        ),
                        const SizedBox(height: 5),
                        const Text(
                          'Use a clear, front-facing photo for the best result.',
                          style: TextStyle(
                            color: Color(0xFF7D8490),
                            height: 1.4,
                            fontSize: 13,
                          ),
                        ),
                        const SizedBox(height: 15),
                        Row(
                          children: [
                            _genderButton('Male', 'male'),
                            const SizedBox(width: 8),
                            _genderButton('Female', 'female'),
                          ],
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _isLoading ? null : pickImage,
                            icon: const Icon(Icons.add_photo_alternate_outlined, size: 19),
                            label: const Text('Choose photo'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF238C83),
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(15),
                              ),
                            ),
                          ),
                        ),
                        if (_image != null) ...[
                          const SizedBox(height: 16),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(17),
                            child: Image.memory(
                              _image!,
                              width: double.infinity,
                              height: 250,
                              fit: BoxFit.contain,
                              errorBuilder: (_, __, ___) => const SizedBox(
                                height: 100,
                                child: Center(child: Text('Could not display selected photo.')),
                              ),
                            ),
                          ),
                          if (_imageName != null) ...[
                            const SizedBox(height: 8),
                            Text(
                              _imageName!,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: Color(0xFF7D8490),
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  _sectionCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'New: Landmark alignment test',
                          style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
                        ),
                        const SizedBox(height: 5),
                        const Text(
                          'Calculate landmark NME and error reduction using the fixed reference-user landmark JSON. No comparison preview images are generated.',
                          style: TextStyle(color: Color(0xFF7D8490), fontSize: 13, height: 1.4),
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _image == null || _isAlignmentLoading
                                ? null
                                : runAlignmentComparison,
                            icon: _isAlignmentLoading
                                ? const SizedBox(
                                    width: 17,
                                    height: 17,
                                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                  )
                                : const Icon(Icons.compare_arrows),
                            label: Text(_isAlignmentLoading
                                ? 'Comparing alignment…'
                                : 'Run alignment comparison'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF176E68),
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (_alignmentResult != null) ...[
                    const SizedBox(height: 16),
                    _alignmentComparisonCard(),
                  ],
                  if (_isLoading) ...[
                    const SizedBox(height: 16),
                    _sectionCard(
                      child: const Row(
                        children: [
                          SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.5,
                              color: Color(0xFF238C83),
                            ),
                          ),
                          SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              'Finding your best match…',
                              style: TextStyle(
                                color: Color(0xFF176E68),
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  if (normalUrl != null) ...[
                    const SizedBox(height: 18),
                    _sectionCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Expanded(
                                child: Text(
                                  'Recommended look',
                                  style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800),
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFDDF7E8),
                                  borderRadius: BorderRadius.circular(30),
                                ),
                                child: const Text(
                                  'MATCH',
                                  style: TextStyle(
                                    color: Color(0xFF18834A),
                                    fontWeight: FontWeight.w900,
                                    fontSize: 11,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 13),

                          // Before / After: original photo and recommended look.
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text(
                                      'Before',
                                      style: TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w800,
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    ClipRRect(
                                      borderRadius: BorderRadius.circular(12),
                                      child: _image != null
                                          ? Image.memory(
                                              _image!,
                                              width: double.infinity,
                                              height: 190,
                                              fit: BoxFit.contain,
                                              errorBuilder: (_, __, ___) =>
                                                  const SizedBox(
                                                height: 190,
                                                child: Center(
                                                  child: Text(
                                                    'Could not display original photo.',
                                                    textAlign: TextAlign.center,
                                                  ),
                                                ),
                                              ),
                                            )
                                          : const SizedBox(
                                              height: 190,
                                              child: Center(
                                                child: Text('No original photo'),
                                              ),
                                            ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text(
                                      'After',
                                      style: TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w800,
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    ClipRRect(
                                      borderRadius: BorderRadius.circular(12),
                                      child: Image.network(
                                        normalUrl,
                                        width: double.infinity,
                                        height: 190,
                                        fit: BoxFit.contain,
                                        errorBuilder: (_, __, ___) =>
                                            const SizedBox(
                                          height: 190,
                                          child: Center(
                                            child: Text(
                                              'Could not load recommended preview.',
                                              textAlign: TextAlign.center,
                                            ),
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          if (currentStyle != null) ...[
                            const SizedBox(height: 13),
                            Text(
                              currentStyle!,
                              style: const TextStyle(
                                fontSize: 21,
                                fontWeight: FontWeight.w800,
                                color: Color(0xFF20232A),
                              ),
                            ),
                          ],
                          if (currentVariant != null) ...[
                            const SizedBox(height: 4),
                            Text(
                              currentVariant!,
                              style: const TextStyle(
                                color: Color(0xFF7D8490),
                                fontSize: 13,
                              ),
                            ),
                          ],
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              const Expanded(
                                child: Text(
                                  'Compatibility',
                                  style: TextStyle(
                                    color: Color(0xFF7D8490),
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                              Text(
                                'Rank #$currentRank',
                                style: const TextStyle(
                                  color: Color(0xFF176E68),
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(20),
                            child: const LinearProgressIndicator(
                              value: 0.88,
                              minHeight: 8,
                              backgroundColor: Color(0xFFE9EBEF),
                              color: Color(0xFF238C83),
                            ),
                          ),
                          if (_explanation != null) ...[
                            const SizedBox(height: 13),
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(
                                  Icons.info_outline,
                                  size: 19,
                                  color: Color(0xFF7D8490),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    _explanation!,
                                    style: const TextStyle(
                                      color: Color(0xFF656C77),
                                      height: 1.5,
                                      fontSize: 14,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                          const SizedBox(height: 18),
                          const Text(
                            'Do you like this style?',
                            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15),
                          ),
                          const SizedBox(height: 10),
                          Row(
                            children: [
                              Expanded(
                                child: OutlinedButton.icon(
                                  onPressed: _isLoading || _isAdvancedLoading
                                      ? null
                                      : () => sendFeedback('dislike'),
                                  icon: const Icon(Icons.close_rounded),
                                  label: const Text('Try another'),
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: const Color(0xFF555D68),
                                    side: const BorderSide(color: Color(0xFFE2E5E9)),
                                    padding: const EdgeInsets.symmetric(vertical: 13),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(15),
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: ElevatedButton.icon(
                                  onPressed: _isLoading || _isAdvancedLoading
                                      ? null
                                      : () => sendFeedback('like'),
                                  icon: const Icon(Icons.thumb_up_alt_outlined),
                                  label: const Text('I like it'),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: const Color(0xFF238C83),
                                    foregroundColor: Colors.white,
                                    padding: const EdgeInsets.symmetric(vertical: 13),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(15),
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                  if (_isAdvancedLoading) ...[
                    const SizedBox(height: 16),
                    _sectionCard(
                      child: const Column(
                        children: [
                          CircularProgressIndicator(color: Color(0xFF238C83)),
                          SizedBox(height: 12),
                          Text(
                            'Generating advanced preview…',
                            style: TextStyle(fontWeight: FontWeight.w700),
                          ),
                          SizedBox(height: 4),
                          Text(
                            'This may take a little while.',
                            style: TextStyle(
                              color: Color(0xFF7D8490),
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  if (advancedUrl != null) ...[
                    const SizedBox(height: 18),
                    _sectionCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Advanced AI preview',
                            style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 12),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(17),
                            child: Image.network(
                              advancedUrl,
                              width: double.infinity,
                              fit: BoxFit.contain,
                              errorBuilder: (_, __, ___) => const Text(
                                'Could not load advanced preview image.',
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 18),
                  const Center(
                    child: Text(
                      'Personalized grooming recommendations',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Color(0xFF7D8490),
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
