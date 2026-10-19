# Backend Setup and Testing Guide

## Cause of Current Error
The previous code tried to save the old AnalysisResponse directly as JSON, but profile_service.analyze_profile now returns a tuple (response, detail_dict). This has been fixed.

## Step 1: Start the Server

### 1.1 Check for Port Conflicts
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# If processes are running, kill them:
taskkill /PID [PID_NUMBER] /F
```

Or run: `check_port.bat`

### 1.2 Download FaceDetector Model
```bash
cd backend/grooming_component_1_backend/backend/models
# Run the download script
download_face_detector.bat

# Or download manually from:
# https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite
```

### 1.3 Start Backend
```bash
cd C:\Users\Admin\Desktop\grooming\backend\grooming_component_1_backend
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 2: Verify Flutter Config

Flutter base URL should be: `http://10.0.2.2:8000/analyze_face` (for emulator)

Check: `lib/config/api_config.dart`

## Step 3: Test Cases

### Test A: Half-body photo (face too small)
- Upload a half-body photo where face is ~10-15% of image width
- **Expected**: "Face too small in the image. Move closer..."
- **NOT**: "No face detected"

### Test B: Close-up frontal selfie
- Upload a proper selfie where face fills frame
- **Expected**: Analysis succeeds with hairline/jawline results

### Test C: No person in photo
- Upload a landscape or object photo
- **Expected**: "No face detected in the image..."

### Test D: Multiple people
- Upload a photo with 2+ people
- **Expected**: "Multiple faces detected..."

### Test E: Strongly turned head
- Upload a selfie with head turned left/right significantly
- **Expected**: Pose rejection message about rotation

## Step 4: Verify Outputs

After each test, check:
1. Terminal shows: `POST /analyze_face ... 200`
2. File created: `backend/grooming_component_1_backend/outputs/profiles/<image_name>.json`
3. Accepted images have full structure with model_outputs and landmark_extractions
4. Rejected images have status="rejected" with reason

## Debug Logs

The backend now logs:
- `[DEBUG] Input image size: W x H`
- `[DEBUG] Stage A: Face box width = X px (Y% of image)`
- `[DEBUG] Stage A: Face too small` (if rejected)
- `[DEBUG] Stage B: Face crop size = W x H`
- `[DEBUG] Stage B: Extracted N landmarks`
- `[DEBUG] Pose angles: pitch=X yaw=Y roll=Z`
- `[DEBUG] Jawline angle: X degrees`

Check terminal output during analysis to see where rejection occurs.

## Configuration Values (in mediapipe_service.py __init__)

Current thresholds:
- `min_face_width_ratio`: 0.25 (face must be 25% of image width)
- `min_face_width_px`: 200 (face must be 200+ pixels wide)
- `crop_margin_ratio`: 0.4 (40% margin around detected face)
- `yaw_threshold`: 30.0 degrees
- `pitch_threshold`: 30.0 degrees
- `roll_threshold`: 30.0 degrees

These can be calibrated after testing.
