import 'package:flutter/material.dart';

import 'screens/profile_page.dart';
import 'screens/results_page.dart';
import 'state/app_controller.dart';
import 'theme/app_theme.dart';

class StyleRankerApp extends StatefulWidget {
  const StyleRankerApp({super.key, required this.controller});

  final AppController controller;

  @override
  State<StyleRankerApp> createState() => _StyleRankerAppState();
}

class _StyleRankerAppState extends State<StyleRankerApp> {
  int index = 0;

  @override
  void initState() {
    super.initState();
    widget.controller.refreshConnection();
  }

  String? _notice(AppController controller) {
    if (controller.checking && controller.connectionError == null) {
      return null;
    }
    switch (controller.connectionStatus) {
      case 'ready':
        return null;
      case 'notReady':
        return 'Recommendations are not ready yet.';
      default:
        return 'Recommendations are unavailable right now.';
    }
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      ProfilePage(
        controller: widget.controller,
        onGenerated: () => setState(() => index = 1),
      ),
      ResultsPage(controller: widget.controller),
    ];
    return MaterialApp(
      title: 'Style',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      home: Scaffold(
        appBar: AppBar(
          title: const Text(
            'Style',
            style: TextStyle(
              fontWeight: FontWeight.w700,
              letterSpacing: -0.6,
              color: AppTheme.primaryDarkBlue,
            ),
          ),
        ),
        body: Column(
          children: [
            AnimatedBuilder(
              animation: widget.controller,
              builder: (context, _) {
                if (widget.controller.checking) {
                  return const LinearProgressIndicator(
                    minHeight: 2,
                    color: AppTheme.accent,
                    backgroundColor: Color(0xFFE7F1FB),
                  );
                }
                final message = _notice(widget.controller);
                if (message == null) return const SizedBox.shrink();
                return Padding(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
                  child: Container(
                    padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFF6F5),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.cloud_off_outlined,
                          size: 18,
                          color: Color(0xFFB42318),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            message,
                            style: const TextStyle(color: AppTheme.textPrimary),
                          ),
                        ),
                        TextButton(
                          onPressed: widget.controller.refreshConnection,
                          child: const Text('Try again'),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
            Expanded(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final wide = constraints.maxWidth >= 900;
                  if (wide) {
                    return Row(
                      children: [
                        NavigationRail(
                          selectedIndex: index,
                          onDestinationSelected: (value) =>
                              setState(() => index = value),
                          labelType: NavigationRailLabelType.all,
                          destinations: const [
                            NavigationRailDestination(
                              icon: Icon(Icons.face_retouching_natural_outlined),
                              selectedIcon: Icon(Icons.face_retouching_natural),
                              label: Text('Profile'),
                            ),
                            NavigationRailDestination(
                              icon: Icon(Icons.auto_awesome_outlined),
                              selectedIcon: Icon(Icons.auto_awesome),
                              label: Text('Looks'),
                            ),
                          ],
                        ),
                        const VerticalDivider(width: 1),
                        Expanded(child: pages[index]),
                      ],
                    );
                  }
                  return pages[index];
                },
              ),
            ),
          ],
        ),
        bottomNavigationBar: LayoutBuilder(
          builder: (context, constraints) {
            if (MediaQuery.sizeOf(context).width >= 900) {
              return const SizedBox.shrink();
            }
            return DecoratedBox(
              decoration: const BoxDecoration(
                color: AppTheme.card,
                border: Border(top: BorderSide(color: AppTheme.line)),
              ),
              child: NavigationBar(
                selectedIndex: index,
                onDestinationSelected: (value) => setState(() => index = value),
                destinations: const [
                  NavigationDestination(
                    icon: Icon(Icons.face_retouching_natural_outlined),
                    selectedIcon: Icon(Icons.face_retouching_natural),
                    label: 'Profile',
                  ),
                  NavigationDestination(
                    icon: Icon(Icons.auto_awesome_outlined),
                    selectedIcon: Icon(Icons.auto_awesome),
                    label: 'Looks',
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}
