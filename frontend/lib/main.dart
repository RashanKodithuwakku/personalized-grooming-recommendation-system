import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'screens/select_file_screen.dart';
import 'theme/groom_colors.dart';
import 'theme/groom_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      systemNavigationBarColor: GroomColors.ink,
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );
  runApp(const GroomApp());
}

class GroomApp extends StatelessWidget {
  const GroomApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Groom',
      debugShowCheckedModeBanner: false,
      theme: buildGroomTheme(),
      builder: (context, child) {
        final media = MediaQuery.of(context);
        return MediaQuery(
          data: media.copyWith(
            textScaler: media.textScaler.clamp(minScaleFactor: 0.9, maxScaleFactor: 1.25),
          ),
          child: child ?? const SizedBox.shrink(),
        );
      },
      home: const SelectFileScreen(),
    );
  }
}
