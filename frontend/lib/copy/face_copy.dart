class FaceShapeStory {
  const FaceShapeStory({
    required this.title,
    required this.summary,
    required this.detail,
  });

  final String title;
  final String summary;
  final String detail;
}

const faceShapeStories = <String, FaceShapeStory>{
  'oval': FaceShapeStory(
    title: 'Oval',
    summary: 'A little longer than it is wide, with a softly rounded jaw.',
    detail:
        'The cheekbones are the widest point, and the forehead and jaw stay close to each other in width.',
  ),
  'round': FaceShapeStory(
    title: 'Round',
    summary: 'Width and length sit close together, with full cheeks.',
    detail: 'The outline stays curved, and the jaw reads soft rather than angled.',
  ),
  'square': FaceShapeStory(
    title: 'Square',
    summary: 'Forehead, cheeks, and jaw are similar in width.',
    detail: 'The jaw is the firmer part of the outline, with clearer corners.',
  ),
  'oblong': FaceShapeStory(
    title: 'Oblong',
    summary: 'Noticeably longer than it is wide, with a straighter cheek line.',
    detail: 'The forehead, cheeks, and jaw stay fairly even from top to bottom.',
  ),
  'heart': FaceShapeStory(
    title: 'Heart',
    summary: 'Widest across the forehead, then narrowing toward the chin.',
    detail: 'The lower face tapers, so the chin is the narrowest part of the outline.',
  ),
  'diamond': FaceShapeStory(
    title: 'Diamond',
    summary: 'Widest at the cheekbones, with a narrower forehead and jaw.',
    detail: 'The face draws in both above and below the cheeks.',
  ),
};

const morphologicalCopy = <String, String>{
  'Hypereuryprosopic': 'The face reads very short and wide.',
  'Euryprosopic': 'The face reads short and wide.',
  'Mesoprosopic': 'Length and width sit in a medium range.',
  'Leptoprosopic': 'The face reads longer than it is wide.',
  'Hyperleptoprosopic': 'The face reads very long and narrow.',
};

const jawCopy = <String, String>{
  'angular': 'The jawline looks angled rather than curved.',
  'rounded': 'The jawline looks soft and curved.',
  'tapered': 'The jaw narrows toward the chin.',
};

String shapeTitle(String key) {
  return faceShapeStories[key]?.title ?? _titleCase(key);
}

String readingFailureCopy(String? code) {
  switch (code) {
    case 'LOW_CONFIDENCE':
      return 'The capture behind this file was not clear enough to trust a face shape.';
    case 'MISSING_LANDMARKS':
      return 'This file is missing points the reading needs, such as the chin, cheeks, or jaw corners.';
    default:
      return 'The service could not finish a face reading from this file.';
  }
}

String _titleCase(String key) {
  if (key.isEmpty) return key;
  return key[0].toUpperCase() + key.substring(1);
}
