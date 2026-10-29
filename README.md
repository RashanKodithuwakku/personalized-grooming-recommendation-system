# 💈 Grooming — Facial Profiling App

> An AI-powered mobile application that analyzes facial features to classify **Hairline** and **Jawline** profiles using deep learning and MediaPipe landmark detection.

---

## 🔗 GitHub Repositories

| Repository | Link |
|---|---|
| 📱 **Frontend (Flutter App)** | [github.com/Eshararanaveera/grooming_app_fro](https://github.com/Eshararanaveera/grooming_app_fro) |
| 🐍 **Backend (FastAPI Server)** | [github.com/Eshararanaveera/grooming_app_back](https://github.com/Eshararanaveera/grooming_app_back) |
| 🧠 **ML Model Training** | [github.com/Eshararanaveera/facial_profiling](https://github.com/Eshararanaveera/facial_profiling) |

---

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [Architecture](#-architecture)
- [Frontend — Flutter](#-frontend--flutter)
  - [Tech Stack](#frontend-tech-stack)
  - [Project Structure](#frontend-project-structure)
  - [Screens](#screens)
  - [Services & Models](#services--models)
  - [Configuration](#configuration)
  - [Setup & Run (Frontend)](#setup--run-frontend)
- [Backend — FastAPI](#-backend--fastapi)
  - [Tech Stack](#backend-tech-stack)
  - [Project Structure](#backend-project-structure)
  - [API Endpoints](#api-endpoints)
  - [ML Models](#ml-models)
  - [Services](#backend-services)
  - [Setup & Run (Backend)](#setup--run-backend)
- [Communication Flow](#-communication-flow)
- [Environment & Configuration Guide](#-environment--configuration-guide)
- [Prerequisites](#-prerequisites)
- [Troubleshooting](#-troubleshooting)

---

## 🌟 Project Overview

**Grooming** is a cross-platform mobile application built with Flutter that captures or selects a user's facial photo and sends it to a Python FastAPI backend for AI-powered analysis. The backend uses:

- **MediaPipe Face Landmarker** for landmark detection and head pose estimation
- **EfficientNet-B0** deep learning models (PyTorch) for classifying hairline and jawline types
- **Image quality validation** to ensure the photo meets minimum requirements before analysis

Results are returned to the Flutter app and displayed with confidence scores for both hairline and jawline classifications.

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Flutter App (Frontend)                    │
│                                                                  │
│  HomeScreen ──▶ PhotoUploadScreen ──▶ AnalysisLoadingScreen     │
│                                               │                  │
│                                    AnalysisResultScreen          │
└───────────────────────────┬─────────────────────────────────────┘
                            │  HTTP POST /analyze_face
                            │  (multipart/form-data image upload)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                       │
│                                                                  │
│  main.py (FastAPI app)                                           │
│     │                                                            │
│     ├── QualityService    (blur, brightness, face presence)      │
│     ├── MediaPipeService  (landmarks, head pose estimation)      │
│     ├── ClassifierService (EfficientNet-B0 hairline + jawline)   │
│     └── ProfileService    (orchestrates all services)            │
│                                                                  │
│  ML Models: hairline_efficientnet_b0.pth                        │
│             jawline_efficientnet_b0.pth                          │
│             face_landmarker.task                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📱 Frontend — Flutter

### Frontend Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| Flutter | SDK ^3.13.4 | Cross-platform mobile framework |
| Dart | ^3.13.4 | Programming language |
| `http` | ^1.2.0 | HTTP networking for API calls |
| `image_picker` | 1.1.2 | Camera & gallery image selection |
| `cupertino_icons` | ^1.0.8 | iOS-style icons |

### Frontend Project Structure

```
grooming/
├── lib/
│   ├── main.dart                         # App entry point
│   ├── config/
│   │   └── api_config.dart               # Base URL configuration
│   ├── models/
│   │   └── analysis_result.dart          # AnalysisResult data model
│   ├── services/
│   │   ├── component_1_api_service.dart  # API communication service
│   │   └── image_picker_service.dart     # Image picking utility
│   ├── screens/
│   │   ├── home_screen.dart              # Landing / home screen
│   │   ├── photo_upload_screen.dart      # Camera / gallery upload UI
│   │   ├── analysis_loading_screen.dart  # Loading animation screen
│   │   └── analysis_result_screen.dart  # Results display screen
│   └── widgets/                          # Reusable UI components
├── assets/                               # Static assets (images, fonts)
├── android/                              # Android platform files
├── ios/                                  # iOS platform files
├── pubspec.yaml                          # Dependencies & metadata
└── test/                                 # Unit/widget tests
```

### Screens

| Screen | File | Description |
|---|---|---|
| **Home** | `home_screen.dart` | Landing page with app branding and navigation |
| **Photo Upload** | `photo_upload_screen.dart` | Capture from camera or select from gallery |
| **Analysis Loading** | `analysis_loading_screen.dart` | Animated loading state while API call is in progress |
| **Analysis Result** | `analysis_result_screen.dart` | Displays hairline type, jawline type, and confidence scores |

### Services & Models

#### `Component1ApiService` (`lib/services/component_1_api_service.dart`)
Handles all communication with the FastAPI backend:
- Sends image as a `multipart/form-data` POST request to `/analyze_face`
- 60-second request timeout
- Parses the JSON response into an `AnalysisResult` object
- Gracefully handles `SocketException`, server errors, and unexpected failures

#### `AnalysisResult` (`lib/models/analysis_result.dart`)
Data model representing the backend analysis response:

```dart
class AnalysisResult {
  final String hairlineResult;      // e.g. "High", "Low", "Receding"
  final double hairlineConfidence;  // 0.0 – 1.0
  final String jawlineResult;       // e.g. "Square", "Round", "Oval"
  final double jawlineConfidence;   // 0.0 – 1.0
  final String message;             // Error or info message
  final bool isSuccess;             // true if analysis succeeded
}
```

### Configuration

The base URL for the backend is configured in `lib/config/api_config.dart`:

```dart
class ApiConfig {
  static const String baseUrl = 'http://10.0.2.2:8000';
}
```

| Environment | Base URL |
|---|---|
| Android Emulator | `http://10.0.2.2:8000` *(default)* |
| Physical Android / iOS Device | `http://<YOUR_WIFI_IP>:8000` |
| iOS Simulator / Web / Desktop | `http://localhost:8000` |

> **Change this value** to match your development environment before running the app.

### Setup & Run (Frontend)

#### Prerequisites
- Flutter SDK `>=3.13.4`
- Dart SDK
- Android Studio / Xcode (for emulators)
- A running backend server (see [Backend Setup](#setup--run-backend))

#### Steps

```bash
# 1. Navigate to the project root
cd grooming

# 2. Install dependencies
flutter pub get

# 3. Update the base URL in lib/config/api_config.dart
#    to match your environment (emulator / device / simulator)

# 4. Run on an emulator or connected device
flutter run

# 5. (Optional) Run tests
flutter test
```

---

## 🐍 Backend — FastAPI

### Backend Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Programming language |
| FastAPI | latest | REST API framework |
| Uvicorn | latest | ASGI server |
| PyTorch + Torchvision | latest | Deep learning inference |
| MediaPipe | >=1.0.0 | Face landmark detection & pose estimation |
| EfficientNet-B0 | (custom `.pth`) | Hairline & jawline classification |
| scikit-learn | latest | ML utilities |
| XGBoost | latest | Gradient boosting (auxiliary models) |
| OpenCV | latest | Image processing |
| Pillow | >=10.0.0 | Image I/O and EXIF handling |
| joblib | latest | Model serialization |
| python-multipart | latest | Multipart file upload parsing |

### Backend Project Structure

```
backend/
├── main.py                          # FastAPI app entry point
├── requirements.txt                 # Python dependencies
├── __init__.py
├── models/                          # Pre-trained ML model files
│   ├── hairline_efficientnet_b0.pth # Hairline classifier (EfficientNet-B0)
│   ├── jawline_efficientnet_b0.pth  # Jawline classifier (EfficientNet-B0)
│   ├── face_landmarker.task         # MediaPipe Face Landmarker task model
│   └── download_face_detector.bat   # Script to download face detector
├── schemas/
│   └── profile_schema.py            # Pydantic request/response schemas
├── services/
│   ├── profile_service.py           # Orchestrates analysis pipeline
│   ├── quality_service.py           # Image quality validation
│   ├── mediapipe_service.py         # Landmark detection & pose estimation
│   └── classifier_service.py        # EfficientNet-B0 classification
└── outputs/
    └── profiles/                    # Saved JSON analysis outputs per image
```

### API Endpoints

#### `GET /`
**Health Check**

Returns server status.

```json
{
  "message": "Facial Profiling API is running",
  "status": "healthy"
}
```

---

#### `POST /analyze_face`
**Analyze Facial Image**

Accepts a facial image upload and returns hairline + jawline classification results.

**Request:**
- Content-Type: `multipart/form-data`
- Field: `image` — image file (JPG, PNG, etc.)

**Response (200 OK):**
```json
{
  "hairline_result": "High",
  "hairline_confidence": 0.87,
  "jawline_result": "Square",
  "jawline_confidence": 0.91,
  "message": "",
  "is_success": true
}
```

**Error Responses:**

| Status | Reason |
|---|---|
| `400 Bad Request` | No image provided or empty file |
| `400 Bad Request` | Image quality check failed (blurry, dark, no face detected) |
| `400 Bad Request` | Head pose not front-facing |
| `500 Internal Server Error` | Unexpected server error |

---

### ML Models

| Model File | Type | Purpose |
|---|---|---|
| `hairline_efficientnet_b0.pth` | PyTorch EfficientNet-B0 | Classifies hairline type from facial crop |
| `jawline_efficientnet_b0.pth` | PyTorch EfficientNet-B0 | Classifies jawline type from facial crop |
| `face_landmarker.task` | MediaPipe Tasks | 478-point facial landmark detection |

> **Note:** Model files are large (~16 MB each) and are stored in `backend/models/`. Do **not** commit them to version control. Use Git LFS or provide a download script.

---

### Backend Services

#### `QualityService` (`services/quality_service.py`)
Validates the uploaded image before analysis:
- Checks for minimum resolution
- Detects image blur (Laplacian variance)
- Checks brightness levels
- Confirms face presence in the image

#### `MediaPipeService` (`services/mediapipe_service.py`)
Performs facial landmark detection:
- Uses MediaPipe Face Landmarker (Tasks API, `mediapipe>=1.0.0`)
- Extracts 478 face landmarks
- Estimates head pose (yaw, pitch, roll) to ensure front-facing photo

#### `ClassifierService` (`services/classifier_service.py`)
Runs deep learning classification:
- Loads `hairline_efficientnet_b0.pth` and `jawline_efficientnet_b0.pth`
- Pre-processes the facial crop for EfficientNet input
- Returns predicted class label and confidence score for both hairline and jawline

#### `ProfileService` (`services/profile_service.py`)
Orchestrates the full pipeline:
1. Calls `QualityService` — validates image
2. Calls `MediaPipeService` — detects landmarks, checks pose
3. Calls `ClassifierService` — classifies hairline & jawline
4. Returns structured `AnalysisResponse`
5. Saves detailed JSON output to `outputs/profiles/`

---

### Setup & Run (Backend)

#### Prerequisites
- Python **3.10+**
- `pip`
- CUDA-compatible GPU *(optional, but recommended for faster inference)*

#### Steps

```bash
# 1. Navigate to the backend directory
cd grooming/backend

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Ensure ML model files are in place:
#    backend/models/hairline_efficientnet_b0.pth
#    backend/models/jawline_efficientnet_b0.pth
#    backend/models/face_landmarker.task
#    (Run download_face_detector.bat if face_landmarker.task is missing)

# 5. Start the FastAPI server from the grooming root directory
cd ..
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **Local:** `http://localhost:8000`
- **Swagger UI / Docs:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 🔄 Communication Flow

```
User taps "Analyze" in Flutter App
          │
          ▼
ImagePickerService picks photo (camera or gallery)
          │
          ▼
Component1ApiService sends POST /analyze_face
  with image as multipart/form-data
          │
          ▼
FastAPI Backend receives image
  │
  ├─ QualityService validates image
  │     (blur, brightness, face presence)
  │
  ├─ MediaPipeService detects landmarks
  │     (head pose check: must be front-facing)
  │
  └─ ClassifierService runs EfficientNet-B0
        (hairline classification)
        (jawline classification)
          │
          ▼
AnalysisResponse JSON returned to Flutter
          │
          ▼
AnalysisResultScreen displays:
  - Hairline type + confidence
  - Jawline type + confidence
```

---

## 🌐 Environment & Configuration Guide

### Android Emulator (default setup)
1. Set `ApiConfig.baseUrl = 'http://10.0.2.2:8000'`
2. Start backend on your PC at port `8000`
3. Run the Flutter app on the Android Emulator

### Physical Device (same Wi-Fi network)
1. Find your PC's local IP: `ipconfig` (Windows) / `ifconfig` (macOS/Linux)
2. Set `ApiConfig.baseUrl = 'http://<YOUR_PC_IP>:8000'`
3. Start the backend with `--host 0.0.0.0`
4. Run the Flutter app on your physical device

### iOS Simulator / Web / Desktop
1. Set `ApiConfig.baseUrl = 'http://localhost:8000'`
2. Start the backend normally

---

## ✅ Prerequisites

| Tool | Version | Install |
|---|---|---|
| Flutter | >=3.13.4 | [flutter.dev](https://flutter.dev/docs/get-started/install) |
| Dart | >=3.13.4 | Bundled with Flutter |
| Python | >=3.10 | [python.org](https://python.org) |
| pip | latest | Bundled with Python |
| Android Studio | latest | For Android emulator |
| Xcode | latest (macOS only) | For iOS simulator |

---

## 🔧 Troubleshooting

### Backend won't start
- Ensure Python 3.10+ is installed: `python --version`
- Activate the virtual environment before installing/running
- Verify all model files exist in `backend/models/`
- Check port 8000 is not in use: run `check_port.bat` (Windows)

### Flutter can't connect to backend
- Confirm the backend is running: visit `http://localhost:8000/docs`
- Check `ApiConfig.baseUrl` matches your environment
- For Android Emulator, use `10.0.2.2` not `localhost`
- Ensure your firewall allows connections on port 8000

### Image analysis fails
- Ensure the photo is **well-lit**, **in focus**, and shows a **front-facing face**
- The backend performs quality checks; blurry or dark images will be rejected
- Head must be facing forward (yaw/pitch within acceptable range)

### MediaPipe errors
- Backend requires `mediapipe>=1.0.0` (legacy `mp.solutions` API was removed)
- Ensure `face_landmarker.task` is present in `backend/models/`

---

## 📄 License

This project is private and not published to pub.dev.

---

## 👥 Contributors

Built with ❤️ using Flutter + FastAPI + PyTorch.
