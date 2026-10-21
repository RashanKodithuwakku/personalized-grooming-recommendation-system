const facialConfidenceKeys = <String>[
  'face_length_ratio',
  'jaw_width_ratio',
  'upper_width_ratio',
  'lower_face_ratio',
  'face_shape',
  'jawline',
  'forehead',
  'hairline',
  'symmetry',
];

const faceShapes = ['diamond', 'heart', 'oblong', 'oval', 'round', 'square'];
const jawlines = ['angular', 'rounded', 'soft'];
const foreheads = ['high', 'low', 'medium'];
const hairlines = ['receding', 'rounded', 'straight', 'widows_peak'];
const genders = ['male', 'female'];

/// Demo profiles copied from backend/examples (not real reviewed users).
const maleDemoProfile = <String, Object>{
  'face_length_ratio': 1.1075061748845896,
  'jaw_width_ratio': 0.7981134693568468,
  'upper_width_ratio': 0.8836110941414184,
  'lower_face_ratio': 0.519768052719499,
  'symmetry': 0.8105352571132579,
  'face_shape': 'round',
  'jawline': 'soft',
  'forehead': 'low',
  'hairline': 'straight',
  'gender': 'male',
};

const femaleDemoProfile = <String, Object>{
  'face_length_ratio': 1.4741868136966976,
  'jaw_width_ratio': 0.7022803446346432,
  'upper_width_ratio': 0.8874882194850102,
  'lower_face_ratio': 0.4261109355990833,
  'symmetry': 0.5257072408486533,
  'face_shape': 'round',
  'jawline': 'soft',
  'forehead': 'high',
  'hairline': 'receding',
  'gender': 'female',
};

class StyleRecord {
  StyleRecord({
    required this.styleId,
    required this.category,
    required this.styleName,
    this.definition,
    this.requiresFacialHair = false,
    this.genderRestriction,
  });

  final String styleId;
  final String category;
  final String styleName;
  final String? definition;
  final bool requiresFacialHair;
  final String? genderRestriction;

  factory StyleRecord.fromJson(Map<String, dynamic> json) {
    return StyleRecord(
      styleId: json['style_id'] as String,
      category: json['category'] as String,
      styleName: json['style_name'] as String,
      definition: json['definition'] as String?,
      requiresFacialHair: json['requires_facial_hair'] == true,
      genderRestriction: json['gender_restriction'] as String?,
    );
  }
}

class RecommendationRequestBody {
  RecommendationRequestBody({
    required this.profile,
    required this.categories,
    required this.topN,
    this.includeBeard,
    this.facialHairAvailable,
    this.excludedStyleIds = const [],
    this.attributeConfidence,
    this.rankingMode = 'standard',
    this.confidenceSource = 'unspecified',
  });

  final Map<String, Object> profile;
  final List<String> categories;
  final int topN;
  final bool? includeBeard;
  final bool? facialHairAvailable;
  final List<String> excludedStyleIds;
  final Map<String, double>? attributeConfidence;
  final String rankingMode;
  final String confidenceSource;

  Map<String, dynamic> toJson() {
    final preferences = <String, dynamic>{
      'excluded_style_ids': excludedStyleIds,
    };
    if (includeBeard != null) {
      preferences['include_beard'] = includeBeard;
    }
    if (facialHairAvailable != null) {
      preferences['facial_hair_available'] = facialHairAvailable;
    }
    final body = <String, dynamic>{
      'schema_version': '1.0',
      'profile': profile,
      'categories': categories,
      'top_n': topN,
      'preferences': preferences,
      'ranking_mode': rankingMode,
      'confidence_source': confidenceSource,
    };
    if (attributeConfidence != null && attributeConfidence!.isNotEmpty) {
      body['attribute_confidence'] = attributeConfidence;
    }
    return body;
  }
}

class RuleContribution {
  RuleContribution({
    required this.attribute,
    required this.contribution,
    this.similarity,
    this.weight,
    this.confidence,
    this.effectiveWeight,
    this.supportContribution,
    this.detail,
  });

  final String attribute;
  final double contribution;
  final double? similarity;
  final double? weight;
  final double? confidence;
  final double? effectiveWeight;
  final double? supportContribution;
  final String? detail;

  factory RuleContribution.fromJson(Map<String, dynamic> json) {
    return RuleContribution(
      attribute: json['attribute'] as String,
      contribution: (json['contribution'] as num).toDouble(),
      similarity: (json['similarity'] as num?)?.toDouble(),
      weight: (json['weight'] as num?)?.toDouble(),
      confidence: (json['confidence'] as num?)?.toDouble(),
      effectiveWeight: (json['effective_weight'] as num?)?.toDouble(),
      supportContribution: (json['support_contribution'] as num?)?.toDouble(),
      detail: json['detail'] as String?,
    );
  }
}

class RecommendationItem {
  RecommendationItem({
    required this.rank,
    required this.styleId,
    required this.styleName,
    required this.category,
    required this.rawRankerScore,
    required this.rawPredictedCompatibilityRating,
    required this.displayCompatibilityRating,
    required this.compatibilityScore,
    required this.rankPercentile,
    required this.normalizedPredictedCompatibility,
    required this.hybridScore,
    required this.requiresFacialHair,
    required this.summary,
    this.ruleCompatibilityScore,
    this.ruleConfidenceCoverage,
    this.recommendationSupportScore,
    this.confidenceAdjustedRuleScore,
    this.contributions = const [],
    this.notes = const [],
  });

  final int rank;
  final String styleId;
  final String styleName;
  final String category;
  final double rawRankerScore;
  final double rawPredictedCompatibilityRating;
  final double displayCompatibilityRating;
  final double compatibilityScore;
  final double rankPercentile;
  final double normalizedPredictedCompatibility;
  final double? ruleCompatibilityScore;
  final double? ruleConfidenceCoverage;
  final double? recommendationSupportScore;
  final double? confidenceAdjustedRuleScore;
  final double hybridScore;
  final bool requiresFacialHair;
  final String summary;
  final List<RuleContribution> contributions;
  final List<String> notes;

  factory RecommendationItem.fromJson(Map<String, dynamic> json) {
    final explanation =
        (json['explanation'] as Map?)?.cast<String, dynamic>() ?? {};
    final contribs = (explanation['rule_contributions'] as List?) ?? const [];
    final notes = (explanation['notes'] as List?) ?? const [];
    return RecommendationItem(
      rank: json['rank'] as int,
      styleId: json['style_id'] as String,
      styleName: json['style_name'] as String,
      category: json['category'] as String,
      rawRankerScore: (json['raw_ranker_score'] as num).toDouble(),
      rawPredictedCompatibilityRating:
          (json['raw_predicted_compatibility_rating'] as num).toDouble(),
      displayCompatibilityRating: (json['display_compatibility_rating'] as num)
          .toDouble(),
      compatibilityScore: (json['compatibility_score'] as num).toDouble(),
      rankPercentile: (json['rank_percentile'] as num).toDouble(),
      normalizedPredictedCompatibility:
          (json['normalized_predicted_compatibility'] as num).toDouble(),
      ruleCompatibilityScore: (json['rule_compatibility_score'] as num?)
          ?.toDouble(),
      ruleConfidenceCoverage: (json['rule_confidence_coverage'] as num?)
          ?.toDouble(),
      recommendationSupportScore: (json['recommendation_support_score'] as num?)
          ?.toDouble(),
      confidenceAdjustedRuleScore:
          (json['confidence_adjusted_rule_score'] as num?)?.toDouble(),
      hybridScore: (json['hybrid_score'] as num).toDouble(),
      requiresFacialHair: json['requires_facial_hair'] == true,
      summary: (explanation['summary'] as String?) ?? '',
      contributions: contribs
          .map(
            (e) =>
                RuleContribution.fromJson((e as Map).cast<String, dynamic>()),
          )
          .toList(),
      notes: notes.map((e) => e.toString()).toList(),
    );
  }
}

class CategoryResult {
  CategoryResult({
    required this.category,
    required this.status,
    required this.eligibleCount,
    required this.returnedCount,
    this.recommendations = const [],
    this.emptyReason,
    this.disposition,
    this.dispositionReasons = const [],
    this.dispositionExplanation,
    this.inputQualityScore,
    this.qualityAssessment,
    this.qualityStatus,
  });

  final String category;
  final String status;
  final int eligibleCount;
  final int returnedCount;
  final List<RecommendationItem> recommendations;
  final String? emptyReason;
  final String? disposition;
  final List<String> dispositionReasons;
  final String? dispositionExplanation;
  final double? inputQualityScore;
  final String? qualityAssessment;
  final String? qualityStatus;

  factory CategoryResult.fromJson(Map<String, dynamic> json) {
    final quality = (json['category_input_quality'] as Map?)
        ?.cast<String, dynamic>();
    final recs = (json['recommendations'] as List?) ?? const [];
    return CategoryResult(
      category: json['category'] as String,
      status: json['status'] as String,
      eligibleCount: json['eligible_count'] as int? ?? 0,
      returnedCount: json['returned_count'] as int? ?? 0,
      recommendations: recs
          .map(
            (e) =>
                RecommendationItem.fromJson((e as Map).cast<String, dynamic>()),
          )
          .toList(),
      emptyReason: json['empty_reason'] as String?,
      disposition: json['recommendation_disposition'] as String?,
      dispositionReasons: ((json['disposition_reasons'] as List?) ?? const [])
          .map((e) => e.toString())
          .toList(),
      dispositionExplanation: json['disposition_explanation'] as String?,
      inputQualityScore: (quality?['input_quality_score'] as num?)?.toDouble(),
      qualityAssessment: quality?['assessment'] as String?,
      qualityStatus: quality?['confidence_status'] as String?,
    );
  }
}

class RankingPolicy {
  RankingPolicy({
    required this.policyName,
    required this.description,
    required this.weights,
    this.fallbackApplied = false,
    this.fallbackReason,
    this.activeRankingMode,
    this.note,
  });

  final String policyName;
  final String description;
  final Map<String, double> weights;
  final bool fallbackApplied;
  final String? fallbackReason;
  final String? activeRankingMode;
  final String? note;

  factory RankingPolicy.fromJson(Map<String, dynamic> json) {
    final rawWeights = (json['weights'] as Map?)?.cast<String, dynamic>() ?? {};
    return RankingPolicy(
      policyName: json['policy_name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      weights: rawWeights.map((k, v) => MapEntry(k, (v as num).toDouble())),
      fallbackApplied: json['fallback_applied'] == true,
      fallbackReason: json['fallback_reason'] as String?,
      activeRankingMode: json['active_ranking_mode'] as String?,
      note: json['note'] as String?,
    );
  }
}

class InputQuality {
  InputQuality({
    required this.confidenceStatus,
    required this.assessment,
    this.inputQualityScore,
    this.confidenceCoverage = 0,
    this.confidenceAttributesMissing = const [],
    this.cautionFlag = false,
    this.cautionReasons = const [],
    this.note,
  });

  final String confidenceStatus;
  final String assessment;
  final double? inputQualityScore;
  final double confidenceCoverage;
  final List<String> confidenceAttributesMissing;
  final bool cautionFlag;
  final List<String> cautionReasons;
  final String? note;

  factory InputQuality.fromJson(Map<String, dynamic> json) {
    return InputQuality(
      confidenceStatus: json['confidence_status'] as String? ?? 'not_provided',
      assessment: json['assessment'] as String? ?? 'unknown',
      inputQualityScore: (json['input_quality_score'] as num?)?.toDouble(),
      confidenceCoverage:
          (json['confidence_coverage'] as num?)?.toDouble() ?? 0,
      confidenceAttributesMissing:
          ((json['confidence_attributes_missing'] as List?) ?? const [])
              .map((e) => e.toString())
              .toList(),
      cautionFlag: json['caution_flag'] == true,
      cautionReasons: ((json['caution_reasons'] as List?) ?? const [])
          .map((e) => e.toString())
          .toList(),
      note: json['note'] as String?,
    );
  }
}

class RecommendationResponse {
  RecommendationResponse({
    required this.raw,
    required this.requestId,
    required this.rankingMode,
    required this.confidenceSource,
    required this.policy,
    required this.inputQuality,
    required this.categoryResults,
    required this.skippedCategories,
    required this.warnings,
    required this.notes,
    this.recommendationConfidence,
    this.recommendationConfidenceStatus = 'not_calibrated',
    this.artifactVersion,
  });

  final Map<String, dynamic> raw;
  final String requestId;
  final String rankingMode;
  final String confidenceSource;
  final RankingPolicy policy;
  final InputQuality inputQuality;
  final List<CategoryResult> categoryResults;
  final List<Map<String, dynamic>> skippedCategories;
  final List<String> warnings;
  final List<String> notes;
  final Object? recommendationConfidence;
  final String recommendationConfidenceStatus;
  final String? artifactVersion;

  factory RecommendationResponse.fromJson(Map<String, dynamic> json) {
    return RecommendationResponse(
      raw: json,
      requestId: json['request_id'] as String? ?? '',
      rankingMode: json['ranking_mode'] as String? ?? 'standard',
      confidenceSource: json['confidence_source'] as String? ?? 'unspecified',
      policy: RankingPolicy.fromJson(
        (json['ranking_policy'] as Map).cast<String, dynamic>(),
      ),
      inputQuality: InputQuality.fromJson(
        (json['input_quality'] as Map).cast<String, dynamic>(),
      ),
      categoryResults: ((json['category_results'] as List?) ?? const [])
          .map(
            (e) => CategoryResult.fromJson((e as Map).cast<String, dynamic>()),
          )
          .toList(),
      skippedCategories: ((json['skipped_categories'] as List?) ?? const [])
          .map((e) => (e as Map).cast<String, dynamic>())
          .toList(),
      warnings: ((json['overall_warnings'] as List?) ?? const [])
          .map((e) => e.toString())
          .toList(),
      notes: ((json['notes'] as List?) ?? const [])
          .map((e) => e.toString())
          .toList(),
      recommendationConfidence: json['recommendation_confidence'],
      recommendationConfidenceStatus:
          json['recommendation_confidence_status'] as String? ??
          'not_calibrated',
      artifactVersion: json['artifact_version'] as String?,
    );
  }
}

/// Client-side checks that mirror the backend contract before a request is sent.
class ProfileValidation {
  static Map<String, String> validateProfile(Map<String, String> textFields) {
    final errors = <String, String>{};
    for (final key in [
      'face_length_ratio',
      'jaw_width_ratio',
      'upper_width_ratio',
      'lower_face_ratio',
      'symmetry',
    ]) {
      final raw = textFields[key]?.trim() ?? '';
      if (raw.isEmpty) {
        errors[key] = 'Required';
        continue;
      }
      final value = double.tryParse(raw);
      if (value == null || value.isNaN || value.isInfinite) {
        errors[key] = 'Enter a finite number';
        continue;
      }
      if (key == 'symmetry' && (value < 0 || value > 1)) {
        errors[key] = 'Symmetry must be within 0–1';
      }
    }
    for (final entry in {
      'face_shape': faceShapes,
      'jawline': jawlines,
      'forehead': foreheads,
      'hairline': hairlines,
      'gender': genders,
    }.entries) {
      final value = textFields[entry.key]?.trim() ?? '';
      if (value.isEmpty) {
        errors[entry.key] = 'Required';
      } else if (!entry.value.contains(value)) {
        errors[entry.key] = 'Unsupported value';
      }
    }
    return errors;
  }

  static Map<String, String> validateConfidence({
    required String rankingMode,
    required Map<String, String> confidenceText,
    required bool confidenceEnabled,
  }) {
    final errors = <String, String>{};
    if (!confidenceEnabled && rankingMode != 'confidence_aware') {
      return errors;
    }
    final parsed = <String, double>{};
    for (final key in facialConfidenceKeys) {
      final raw = confidenceText[key]?.trim() ?? '';
      if (raw.isEmpty) {
        if (rankingMode == 'confidence_aware') {
          errors[key] = 'Required in confidence-aware mode';
        }
        continue;
      }
      final value = double.tryParse(raw);
      if (value == null || value.isNaN || value.isInfinite) {
        errors[key] = 'Enter a finite number';
      } else if (value < 0 || value > 1) {
        errors[key] = 'Must be within 0–1';
      } else {
        parsed[key] = value;
      }
    }
    final complete = parsed.length == facialConfidenceKeys.length;
    if (rankingMode == 'confidence_aware' && !complete && errors.isEmpty) {
      errors['_form'] =
          'Confidence-aware mode needs all nine facial confidence values. Zero is allowed. Gender is not one of the nine.';
    }
    if (rankingMode != 'confidence_aware' &&
        parsed.isNotEmpty &&
        !complete &&
        errors.isEmpty) {
      errors['_form'] =
          'Enter all nine facial confidence values or leave them all empty. An incomplete map is not sent.';
    }
    return errors;
  }
}
