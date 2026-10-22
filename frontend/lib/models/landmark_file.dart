import 'dart:typed_data';

class LandmarkFile {
  const LandmarkFile({required this.name, required this.bytes});

  final String name;
  final Uint8List bytes;
}
