import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class EvaluationPage extends StatefulWidget {
  const EvaluationPage({super.key});

  @override
  State<EvaluationPage> createState() => _EvaluationPageState();
}

class _EvaluationPageState extends State<EvaluationPage> {
  String? provenance;
  List<List<String>> rows = const [];
  String? error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final csv = await rootBundle.loadString(
        'assets/evaluation/gender_evaluation.csv',
      );
      final note = await rootBundle.loadString(
        'assets/evaluation/PROVENANCE.txt',
      );
      final lines = csv.trim().split(RegExp(r'\r?\n'));
      setState(() {
        provenance = note;
        rows = lines.map((line) => line.split(',')).toList();
      });
    } catch (_) {
      setState(() {
        error = 'Evaluation asset could not be loaded.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          'Recorded evaluation',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const Text(
          'These offline metrics measure agreement with rule-generated ratings. They are not live request outputs and they are not human suitability accuracy. Top-choice agreement, NDCG@3, MAE, and RMSE keep their recorded names.',
        ),
        const SizedBox(height: 12),
        if (error != null) Text(error!),
        if (provenance != null) Text(provenance!),
        const SizedBox(height: 12),
        const Text('Source file: gender_evaluation.csv'),
        const Text(
          'Run identifier: Component3_GenderAware_20261008T123658_164628Z',
        ),
        const Text(
          'ranker_top_choice_agreement is top-choice agreement. '
          'ranker_ndcg_at_3 is NDCG@3. scorer_mae is MAE. scorer_rmse is RMSE.',
        ),
        const SizedBox(height: 12),
        if (rows.isNotEmpty)
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              columns: [
                for (final cell in rows.first) DataColumn(label: Text(cell)),
              ],
              rows: [
                for (final row in rows.skip(1))
                  DataRow(
                    cells: [for (final cell in row) DataCell(Text(cell))],
                  ),
              ],
            ),
          ),
      ],
    );
  }
}
