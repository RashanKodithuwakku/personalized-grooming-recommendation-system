/// Local photos for catalogue styles.
///
/// Files live in `assets/styles/{gender}/{category}/{style_slug}.jpg`.
/// The slug is the style name with punctuation turned into underscores.
String? styleImageAsset({
  required String styleName,
  required String category,
  String? gender,
}) {
  final slug = styleSlug(styleName);
  final folder = _folder(category);
  if (slug.isEmpty || folder == null) return null;
  final groups = gender == 'female' || gender == 'male'
      ? <String>[gender!]
      : const <String>['male', 'female'];
  for (final group in groups) {
    final key = '$group/$folder/$slug';
    if (_photos.contains(key)) return 'assets/styles/$key.jpg';
  }
  return null;
}

String? styleBlurb(String styleName) => _blurbs[styleSlug(styleName)];

String styleSlug(String name) {
  return name
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '_')
      .replaceAll(RegExp(r'^_|_$'), '');
}

String? _folder(String category) {
  switch (category) {
    case 'hair':
    case 'beard':
    case 'grooming':
      return category;
    default:
      return null;
  }
}

const _blurbs = <String, String>{
  'crew_cut': 'Short hair on top with closely cut sides.',
  'textured_crop': 'Short textured top with a forward fringe.',
  'side_part': 'Hair styled with a visible side part.',
  'layered_cut': 'A haircut with several lengths through the layers.',
  'bob_cut': 'A bob haircut around chin to shoulder length.',
  'pixie_cut': 'A short pixie with a shaped top and sides.',
  'shoulder_length_layers': 'A shoulder-length cut with graduated layers.',
  'long_layers': 'A longer cut with layers below the shoulders.',
  'clean_shaven': 'Beard and moustache hair removed.',
  'short_stubble': 'Very short visible facial-hair stubble.',
  'short_boxed_beard': 'A short beard along the jaw and chin.',
  'goatee': 'Facial hair concentrated around the chin and mouth.',
  'natural_brow_maintenance': 'The natural brow shape, lightly tidied.',
  'straight_brow_styling': 'A predominantly straight eyebrow outline.',
  'soft_angled_brow_styling': 'A brow outline with a gentle arch.',
  'rounded_brow_styling': 'A brow outline with a softly rounded arch.',
};

const _photos = <String>{
  'male/hair/crew_cut',
  'male/hair/side_part',
  'male/hair/textured_crop',
  'male/hair/layered_cut',
  'male/hair/bob_cut',
  'male/hair/pixie_cut',
  'male/hair/shoulder_length_layers',
  'male/hair/long_layers',
  'male/hair/low_fade',
  'male/hair/pompadour',
  'male/hair/slick_back',
  'male/beard/clean_shaven',
  'male/beard/short_stubble',
  'male/beard/short_boxed_beard',
  'male/beard/goatee',
  'male/beard/full_beard',
  'male/beard/van_dyke',
  'male/beard/anchor_beard',
  'male/beard/circle_beard',
  'male/grooming/natural_brow_maintenance',
  'male/grooming/straight_brow_styling',
  'male/grooming/soft_angled_brow_styling',
  'male/grooming/rounded_brow_styling',
  'male/grooming/clean_defined_brows',
  'female/hair/bob_cut',
  'female/hair/side_part',
  'female/hair/pixie_cut',
  'female/hair/textured_crop',
  'female/hair/layered_cut',
  'female/hair/shoulder_length_layers',
  'female/hair/long_layers',
  'female/hair/high_ponytail',
  'female/hair/sleek_straight_hair',
  'female/hair/long_bob',
  'female/hair/curtain_bangs',
  'female/hair/soft_waves',
  'female/grooming/natural_brow_maintenance',
  'female/grooming/straight_brow_styling',
  'female/grooming/soft_angled_brow_styling',
  'female/grooming/rounded_brow_styling',
  'female/grooming/high_arch_brows',
};
