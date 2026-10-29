
import 'package:flutter_test/flutter_test.dart';
import 'package:grooming_component4/main.dart';

void main() {
  testWidgets('Style preview screen loads', (WidgetTester tester) async {
    await tester.pumpWidget(MyApp());

    expect(find.text('Style Preview'), findsOneWidget);
    expect(find.text('Male'), findsOneWidget);
    expect(find.text('Female'), findsOneWidget);
    expect(find.text('Upload Photo'), findsOneWidget);
  });
}
