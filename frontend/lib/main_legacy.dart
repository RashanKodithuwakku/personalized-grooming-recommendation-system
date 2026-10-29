import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'dart:io';
import 'dart:convert';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: PreviewScreen(),
    );
  }
}

class PreviewScreen extends StatefulWidget {
  @override
  _PreviewScreenState createState() => _PreviewScreenState();
}

class _PreviewScreenState extends State<PreviewScreen> {
  File? _image;
  String? _explanation;
  String? _previewPath;
  int currentRank = 1;
  String selectedGender = "male";
  String selectedStyleType = "hairstyle";  // ALUTH VARIABLE - "hairstyle" ho "beard"
  String? currentStyle;
  String? currentVariant;

  Future<void> pickImage() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery);
    if (picked != null) {
      setState(() {
        _image = File(picked.path);
        currentRank = 1;  // Aluth image ekak upload kaloth, rank eka reset karanawa
      });
      await uploadAndGetPreview();
    }
  }

  Future<void> uploadAndGetPreview() async {
    var uri = Uri.parse(
      "http://127.0.0.1:8000/generate-preview"
      "?gender=$selectedGender"
      "&style_type=$selectedStyleType"
      "&current_rank=$currentRank"
    );
    var request = http.MultipartRequest('POST', uri);
    request.files.add(await http.MultipartFile.fromPath('file', _image!.path));

    var response = await request.send();
    var responseData = await response.stream.bytesToString();
    var data = jsonDecode(responseData);

    if (data.containsKey('error')) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error: ${data['error']}")),
      );
      return;
    }

    setState(() {
      _explanation = data['explanation'];
      _previewPath = data['preview_path'];
      currentStyle = data['style'];
      currentVariant = data['variant'];
    });
  }

  // User, "Hairstyle" ho "Beard" button eka click kaloth, mēka call wenawa
  void switchStyleType(String newType) {
    setState(() {
      selectedStyleType = newType;
      currentRank = 1;  // Category eka venas kaloth, rank 1 ekata reset karanawa
    });
    if (_image != null) {
      uploadAndGetPreview();  // Aluth category ekatama, preview eka aye generate karanawa
    }
  }

  Future<void> sendFeedback(String value) async {
    var uri = Uri.parse("http://127.0.0.1:8000/feedback");
    await http.post(
      uri,
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "user_id": "test_user",
        "current_rank": currentRank,
        "feedback_value": value,
        "style_shown": currentStyle ?? "",
        "variant_shown": currentVariant ?? "",
        "gender": selectedGender,
        "style_type": selectedStyleType,
      }),
    );

    if (value == 'dislike') {
      setState(() {
        currentRank++;
      });
      if (_image != null) {
        await uploadAndGetPreview();
      }
    } else if (value == 'like') {
      showAdvancedPreviewPopup();
    }
  }

  void showAdvancedPreviewPopup() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: Text("Want an advanced preview?"),
        content: Text(
          "Would you like to see a more realistic version of this style, "
          "using AI-powered rendering?"
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              sendAdvancedPreviewChoice(false);
            },
            child: Text("No, keep current"),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              sendAdvancedPreviewChoice(true);
            },
            child: Text("Yes, show advanced"),
          ),
        ],
      ),
    );
  }

  Future<void> sendAdvancedPreviewChoice(bool wantsAdvanced) async {
    var uri = Uri.parse("http://127.0.0.1:8000/advanced-preview-choice");

    var response = await http.post(
      uri,
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"wants_advanced": wantsAdvanced}),
    );

    var data = jsonDecode(response.body);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(data["message"])),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Style Preview")),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Gender selection eka
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Radio<String>(
                  value: "male",
                  groupValue: selectedGender,
                  onChanged: (val) => setState(() => selectedGender = val!),
                ),
                Text("Male"),
                Radio<String>(
                  value: "female",
                  groupValue: selectedGender,
                  onChanged: (val) => setState(() => selectedGender = val!),
                ),
                Text("Female"),
              ],
            ),

            if (_image != null) Image.file(_image!, height: 200),

            ElevatedButton(onPressed: pickImage, child: Text("Upload Photo")),

            SizedBox(height: 16),

            // ALUTH — Hairstyle / Beard preview select karana buttons dekak
            if (_image != null)
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ElevatedButton(
                    onPressed: () => switchStyleType("hairstyle"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: selectedStyleType == "hairstyle"
                          ? Colors.blue
                          : Colors.grey[300],
                    ),
                    child: Text("Hairstyle Preview"),
                  ),
                  SizedBox(width: 10),
                  ElevatedButton(
                    onPressed: selectedGender == "male"
                        ? () => switchStyleType("beard")
                        : null,  // Female ekata, beard button eka disable karanawa
                    style: ElevatedButton.styleFrom(
                      backgroundColor: selectedStyleType == "beard"
                          ? Colors.blue
                          : Colors.grey[300],
                    ),
                    child: Text("Beard Preview"),
                  ),
                ],
              ),

            SizedBox(height: 16),

            if (_explanation != null)
              Padding(
                padding: EdgeInsets.all(16),
                child: Text(_explanation!, textAlign: TextAlign.center),
              ),

            if (_explanation != null)
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    icon: Icon(Icons.thumb_up),
                    onPressed: () => sendFeedback('like'),
                  ),
                  IconButton(
                    icon: Icon(Icons.thumb_down),
                    onPressed: () => sendFeedback('dislike'),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}