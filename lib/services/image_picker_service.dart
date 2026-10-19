import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:image_picker/image_picker.dart';

/// Wrapper around image_picker that enforces consistent constraints for both
/// camera and gallery sources:
///   - maxWidth: 1280 px — large enough for EfficientNet-B0 (224×224 input)
///                          but small enough to avoid slow uploads.
///   - imageQuality: 90  — forces JPEG encoding on HEIC/HEIF sources (iOS) and
///                          keeps file size manageable.
///
/// These values are intentionally identical for camera and gallery so the
/// backend always receives the same image format regardless of source.
class ImagePickerService {
  final ImagePicker _picker = ImagePicker();

  static const int _maxWidth = 1280;
  static const int _imageQuality = 90;

  Future<File?> pickImageFromCamera() async {
    try {
      final XFile? pickedFile = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: _maxWidth.toDouble(),
        imageQuality: _imageQuality,
      );
      if (pickedFile != null) {
        debugPrint('Camera — picked: ${pickedFile.path}');
        return File(pickedFile.path);
      }
    } catch (e) {
      debugPrint('Error picking image from camera: $e');
      rethrow;
    }
    return null;
  }

  Future<File?> pickImageFromGallery() async {
    try {
      final XFile? pickedFile = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: _maxWidth.toDouble(),
        imageQuality: _imageQuality,
      );
      if (pickedFile != null) {
        debugPrint('Gallery — picked: ${pickedFile.path}');
        return File(pickedFile.path);
      }
    } catch (e) {
      debugPrint('Error picking image from gallery: $e');
      rethrow;
    }
    return null;
  }
}
