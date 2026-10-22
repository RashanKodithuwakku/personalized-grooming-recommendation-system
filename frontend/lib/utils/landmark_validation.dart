import 'dart:convert';
import 'dart:typed_data';

const maxLandmarkBytes = 2 * 1024 * 1024;

String? validateLandmarkBytes(Uint8List bytes) {
  if (bytes.isEmpty) {
    return 'That file is empty. Choose a landmark JSON file.';
  }
  if (bytes.length > maxLandmarkBytes) {
    return 'That file is larger than 2 MB. Choose the landmark JSON.';
  }
  try {
    final decoded = jsonDecode(utf8.decode(_withoutBom(bytes)));
    if (decoded is! Map) {
      return 'This JSON is not a face reading. Choose the landmark file for one face.';
    }
  } on FormatException {
    return 'This file is not valid JSON. Choose a .json landmark file.';
  }
  return null;
}

Uint8List _withoutBom(Uint8List bytes) {
  if (bytes.length >= 3 &&
      bytes[0] == 0xEF &&
      bytes[1] == 0xBB &&
      bytes[2] == 0xBF) {
    return Uint8List.sublistView(bytes, 3);
  }
  return bytes;
}
