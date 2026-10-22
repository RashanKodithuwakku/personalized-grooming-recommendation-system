class ShapeMatch {
  const ShapeMatch({required this.name, required this.score});

  final String name;
  final double score;
}

/// Display model for `POST /v1/profile`. Scores from the service are 0–1,
/// except [groomingSuitabilityIndex], which is already 0–100.
class FacialProfile {
  const FacialProfile({
    required this.status,
    this.errorCode,
    this.faceShapeLabel,
    this.faceShapeClass,
    this.confidence = const {},
    this.symmetryScore,
    this.verticalBalanceScore,
    this.horizontalBalanceScore,
    this.balanceScore,
    this.groomingSuitabilityIndex,
    this.jawlineCategory,
    this.processingNotes = const [],
  });

  final String status;
  final String? errorCode;
  final String? faceShapeLabel;
  final String? faceShapeClass;
  final Map<String, double> confidence;
  final double? symmetryScore;
  final double? verticalBalanceScore;
  final double? horizontalBalanceScore;
  final double? balanceScore;
  final double? groomingSuitabilityIndex;
  final String? jawlineCategory;
  final List<String> processingNotes;

  bool get failed => status == 'error' || faceShapeLabel == null;

  bool get limited => status == 'limited_analysis';

  double? get leadingScore {
    final label = faceShapeLabel;
    if (label == null) return null;
    return confidence[label];
  }

  List<ShapeMatch> get rankedShapes {
    const order = ['oval', 'round', 'square', 'oblong', 'heart', 'diamond'];
    final names = <String>{...order, ...confidence.keys};
    final matches = [
      for (final name in names) ShapeMatch(name: name, score: confidence[name] ?? 0),
    ]..sort((a, b) {
        final byScore = b.score.compareTo(a.score);
        if (byScore != 0) return byScore;
        return _shapeOrder(order, a.name).compareTo(_shapeOrder(order, b.name));
      });
    return matches;
  }

  factory FacialProfile.fromJson(Map<String, dynamic> json) {
    final rawConfidence = json['face_shape_confidence'];
    final confidence = <String, double>{};
    if (rawConfidence is Map) {
      for (final entry in rawConfidence.entries) {
        final score = _asDouble(entry.value);
        if (score != null) confidence[entry.key.toString()] = score;
      }
    }

    final notes = json['processing_notes'];
    return FacialProfile(
      status: json['status']?.toString() ?? 'ok',
      errorCode: json['error_code']?.toString(),
      faceShapeLabel: json['face_shape_label']?.toString(),
      faceShapeClass: json['face_shape_class']?.toString(),
      confidence: confidence,
      symmetryScore: _asDouble(json['symmetry_score']),
      verticalBalanceScore: _asDouble(json['vertical_balance_score']),
      horizontalBalanceScore: _asDouble(json['horizontal_balance_score']),
      balanceScore: _asDouble(json['balance_score']),
      groomingSuitabilityIndex: _asDouble(json['grooming_suitability_index']),
      jawlineCategory: json['jawline_category']?.toString(),
      processingNotes: notes is List
          ? [for (final note in notes) note.toString()]
          : const [],
    );
  }
}

int _shapeOrder(List<String> order, String name) {
  final index = order.indexOf(name);
  return index < 0 ? order.length : index;
}

double? _asDouble(Object? value) {
  if (value is num) return value.toDouble();
  return null;
}
