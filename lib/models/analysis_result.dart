class AnalysisResult {
  final String hairlineResult;
  final double hairlineConfidence;
  final String jawlineResult;
  final double jawlineConfidence;
  final String message;
  final bool isSuccess;

  AnalysisResult({
    required this.hairlineResult,
    required this.hairlineConfidence,
    required this.jawlineResult,
    required this.jawlineConfidence,
    this.message = '',
    this.isSuccess = true,
  });

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    return AnalysisResult(
      hairlineResult: (json['hairline_result'] as String?) ?? '',
      hairlineConfidence: (json['hairline_confidence'] as num?)?.toDouble() ?? 0.0,
      jawlineResult: (json['jawline_result'] as String?) ?? '',
      jawlineConfidence: (json['jawline_confidence'] as num?)?.toDouble() ?? 0.0,
      message: (json['message'] as String?) ?? '',
      isSuccess: (json['is_success'] as bool?) ?? true,
    );
  }
}
