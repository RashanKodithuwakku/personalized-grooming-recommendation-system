String formatBytes(int bytes) {
  if (bytes < 1024) return '$bytes B';
  if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
  return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
}

/// A 0–100 display value. Whole numbers stay whole; everything else keeps
/// one decimal so 78.4 does not collapse into 78.
String formatPoints(double? value) {
  if (value == null || value.isNaN || value.isInfinite) return '—';
  final clamped = value.clamp(0, 100).toDouble();
  if ((clamped - clamped.roundToDouble()).abs() < 0.05) {
    return clamped.round().toString();
  }
  return clamped.toStringAsFixed(1);
}

String formatUnitPercent(double? unit) {
  if (unit == null) return '—';
  return formatPoints(unit * 100);
}
