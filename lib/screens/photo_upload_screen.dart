import 'dart:io';
import 'package:flutter/material.dart';
import '../services/image_picker_service.dart';
import 'analysis_loading_screen.dart';

class PhotoUploadScreen extends StatefulWidget {
  const PhotoUploadScreen({super.key});

  @override
  State<PhotoUploadScreen> createState() => _PhotoUploadScreenState();
}

class _PhotoUploadScreenState extends State<PhotoUploadScreen> {
  final ImagePickerService _imagePickerService = ImagePickerService();
  File? _selectedImage;
  bool _isLoading = false;

  Future<void> _pickImage(bool fromCamera) async {
    setState(() {
      _isLoading = true;
    });

    try {
      final File? image = fromCamera
          ? await _imagePickerService.pickImageFromCamera()
          : await _imagePickerService.pickImageFromGallery();

      if (!mounted) return;

      if (image != null) {
        debugPrint('Picked image: ${image.path}');
        debugPrint('Image file exists: ${image.existsSync()}');
        debugPrint('Image file length: ${await image.length()} bytes');
        
        setState(() {
          _selectedImage = image;
        });
        
        // Verify after setState
        debugPrint('After setState - _selectedImage: $_selectedImage');
      } else {
        debugPrint('Image picker returned null');
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No image selected.')), // informs user
        );
      }
    } catch (e) {
      debugPrint('Error in _pickImage: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to pick image: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _clearImage() {
    setState(() {
      _selectedImage = null;
    });
  }

  void _analyzeFace() {
    debugPrint('_analyzeFace called. _selectedImage is: $_selectedImage');
    debugPrint('_selectedImage path: ${_selectedImage?.path}');
    
    if (_selectedImage == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No image selected. Please select an image first.')),
      );
      return;
    }
    
    // Verify file exists before navigation
    if (!_selectedImage!.existsSync()) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Selected image file not found. Please select again.')),
      );
      setState(() {
        _selectedImage = null;
      });
      return;
    }
    
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => AnalysisLoadingScreen(imageFile: _selectedImage!),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Upload Photo'),
        actions: [
          if (_selectedImage != null)
            IconButton(
              icon: const Icon(Icons.delete_outline),
              tooltip: 'Remove photo',
              onPressed: _clearImage,
            ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: Container(
                  clipBehavior: Clip.antiAlias,
                  decoration: BoxDecoration(
                    color: Colors.grey[100],
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: _selectedImage != null
                          ? Theme.of(context).primaryColor
                          : Colors.grey[300]!,
                      width: 2,
                    ),
                  ),
                  child: _isLoading
                      ? const Center(child: CircularProgressIndicator())
                      : _selectedImage != null
                          ? Stack(
                              fit: StackFit.expand,
                              children: [
                                Image.file(
                                  _selectedImage!,
                                  key: ValueKey(_selectedImage!.path),
                                  fit: BoxFit.cover,
                                ),
                                Positioned(
                                  top: 12,
                                  right: 12,
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 12, vertical: 6),
                                    decoration: BoxDecoration(
                                      color: Colors.black.withOpacity(0.65),
                                      borderRadius: BorderRadius.circular(20),
                                    ),
                                    child: const Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.check_circle,
                                            color: Colors.greenAccent, size: 16),
                                        SizedBox(width: 6),
                                        Text(
                                          'Selected',
                                          style: TextStyle(
                                            color: Colors.white,
                                            fontSize: 12,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            )
                          : Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.add_a_photo_outlined,
                                  size: 64,
                                  color: Colors.grey[400],
                                ),
                                const SizedBox(height: 16),
                                const Text(
                                  'No Image Selected',
                                  style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.black87,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  'Choose a photo from your gallery or camera\nEnsure face is directly looking at camera',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    fontSize: 13,
                                    color: Colors.grey[600],
                                  ),
                                ),
                              ],
                            ),
                ),
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _isLoading ? null : () => _pickImage(true),
                      icon: const Icon(Icons.camera_alt),
                      label: const Text('Camera'),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _isLoading ? null : () => _pickImage(false),
                      icon: const Icon(Icons.photo_library),
                      label: const Text('Gallery'),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: (_selectedImage == null || _isLoading)
                    ? null
                    : _analyzeFace,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Text(
                  'Analyze Face',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

