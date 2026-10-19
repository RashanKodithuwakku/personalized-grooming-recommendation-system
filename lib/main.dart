import 'package:flutter/material.dart';
import 'utils/app_theme.dart';
import 'screens/photo_upload_screen.dart';

void main() {
  runApp(const FacialProfilingApp());
}

class FacialProfilingApp extends StatelessWidget {
  const FacialProfilingApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Facial Profiling',
      theme: AppTheme.lightTheme,
      home: const PhotoUploadScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}
