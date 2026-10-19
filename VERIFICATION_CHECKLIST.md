# Verification Checklist

## Files Modified
- [x] `backend/grooming_component_1_backend/backend/services/mediapipe_service.py` - Two-stage pipeline
- [x] `backend/grooming_component_1_backend/backend/services/profile_service.py` - Returns tuple
- [x] `backend/grooming_component_1_backend/backend/services/classifier_service.py` - Added detailed methods
- [x] `backend/grooming_component_1_backend/backend/main.py` - Unpacks tuple, saves detail_dict

## Files Created
- [x] `check_port.bat` - Port checking utility
- [x] `backend/grooming_component_1_backend/backend/models/download_face_detector.bat` - Model download
- [x] `BACKEND_SETUP.md` - Complete setup guide
- [x] `IMPLEMENTATION_SUMMARY.md` - Implementation details
- [x] `QUICK_START.txt` - Quick reference
- [x] `test_backend.py` - CLI test script
- [x] `VERIFICATION_CHECKLIST.md` - This file

## Files Verified Unchanged
- [x] `backend/grooming_component_1_backend/.gitignore` - Already has outputs/
- [x] `lib/config/api_config.dart` - Correct base URL
- [x] Flutter response structure - Unchanged

## Pre-Start Checklist

### [ ] 1. Download FaceDetector Model
```bash
cd backend\grooming_component_1_backend\backend\models
download_face_detector.bat
```
Verify: `blaze_face_short_range.tflite` exists (should be ~0.7 MB)

### [ ] 2. Check Port 8000
```bash
netstat -ano | findstr :8000
```
If processes listed, kill them

### [ ] 3. Verify Virtual Environment Path
Current venv: `C:\Users\Admin\Desktop\grooming_component_1_backend\backend\venv`
Project runs from: `C:\Users\Admin\Desktop\grooming\backend\grooming_component_1_backend`

Note: Path mismatch noted. If issues occur, may need to create venv in project directory.

### [ ] 4. Check Required Models Exist
- `backend/grooming_component_1_backend/backend/models/face_landmarker.task` (required)
- `backend/grooming_component_1_backend/backend/models/blaze_face_short_range.tflite` (optional)
- `backend/grooming_component_1_backend/backend/models/hairline_efficientnet_b0.pth` (required)
- `backend/grooming_component_1_backend/backend/models/jawline_efficientnet_b0.pth` (required)

## Test Sequence

### [ ] Test 1: Server Starts
```bash
cd C:\Users\Admin\Desktop\grooming\backend\grooming_component_1_backend
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
**Expected**: 
- FaceDetector initialized (or warning if not found)
- FaceLandmarker initialized
- "Application startup complete"

### [ ] Test 2: Health Check
Open: http://127.0.0.1:8000/
**Expected**: `{"message": "Facial Profiling API is running", "status": "healthy"}`

### [ ] Test 3a: Half-Body Photo (PRIMARY TEST)
Upload a half-body photo where face is ~10-15% of image width

**Terminal logs should show**:
```
[DEBUG] Input image size: W x H
[DEBUG] Stage A: Face box width = X px (<25% of image)
[DEBUG] Stage A: Face too small (ratio=0.XX, px=XXX)
```

**API Response**:
```json
{
  "hairline_result": "",
  "hairline_confidence": 0.0,
  "jawline_result": "",
  "jawline_confidence": 0.0,
  "message": "Face too small in the image. Move closer to the camera...",
  "is_success": false
}
```

**JSON File** (`outputs/profiles/<name>.json`):
```json
{
  "request_id": "req_...",
  "image_name": "...",
  "status": "rejected",
  "reason": "Face too small in the image...",
  "model_outputs": null,
  "landmark_extractions": null
}
```

### [ ] Test 3b: Close-Up Selfie
**Terminal logs should show**:
```
[DEBUG] Input image size: W x H
[DEBUG] Stage A: Face box width = X px (>25% of image)
[DEBUG] Stage B: Face crop size = W x H
[DEBUG] Stage B: Extracted 478 landmarks
[DEBUG] Pose angles: pitch=X yaw=Y roll=Z
[DEBUG] Jawline angle: X degrees
```

**API Response**:
```json
{
  "hairline_result": "straight" or "m_shaped" or "uncertain",
  "hairline_confidence": 0.XX,
  "jawline_result": "angular", "sharp", "soft", or "uncertain",
  "jawline_confidence": 0.XX,
  "message": "Facial profiling analysis completed successfully.",
  "is_success": true
}
```

**JSON File** has full structure with model_outputs and landmark_extractions

### [ ] Test 3c: No Person
**Expected**: "No face detected in the image..."
**NOT**: "Face too small"

### [ ] Test 3d: Multiple People
**Expected**: "Multiple faces detected..."

### [ ] Test 3e: Strongly Turned Head
**Expected**: Pose rejection (yaw/pitch/roll message)

### [ ] Test 4: Flutter Integration
Run Flutter app:
1. Upload photo
2. Press "Analyze Face"
3. Terminal shows: `POST /analyze_face ... 200`
4. Flutter shows result or error message

## Post-Verification Cleanup

After all tests pass:

### [ ] Remove Debug Logs
Edit `backend/grooming_component_1_backend/backend/services/mediapipe_service.py`:
- Search for `logger.info("[DEBUG]`
- Replace with `logger.debug(` (or remove entirely)
- Keep normal INFO logs (initialization, warnings)

### [ ] Calibrate Thresholds (if needed)
Based on test results, adjust in `MediaPipeService.__init__`:
- `min_face_width_ratio` (default: 0.25)
- `min_face_width_px` (default: 200)
- `crop_margin_ratio` (default: 0.4)
- `yaw_threshold`, `pitch_threshold`, `roll_threshold` (default: 30.0)

## Common Issues

### Issue: "No face detected" for half-body photo
**Diagnosis**: FaceDetector model not loaded, falling back to FaceLandmarker-only
**Fix**: Download blaze_face_short_range.tflite

### Issue: Server won't start, "Address already in use"
**Diagnosis**: Port 8000 in use
**Fix**: Kill existing processes on port 8000

### Issue: Import errors
**Diagnosis**: Missing dependencies
**Fix**: `pip install -r backend/grooming_component_1_backend/backend/requirements.txt`

### Issue: "tuple unpacking" error
**Diagnosis**: Old code still running
**Fix**: Stop server (Ctrl+C), restart with --reload

## Success Criteria

✓ Server starts without errors
✓ Half-body photo returns "Face too small" (NOT "No face detected")
✓ Close-up selfie returns analysis results
✓ No person photo returns "No face detected"
✓ Multiple people returns "Multiple faces detected"
✓ Turned head returns pose rejection
✓ Terminal shows [DEBUG] logs for each stage
✓ JSON files saved to outputs/profiles/
✓ Flutter app receives correct responses
✓ Terminal shows POST /analyze_face when Flutter button pressed

## Report Format

**Please report real test results only:**

```
Test A (half-body): 
  Reason: "<actual message>"
  Status: accepted/rejected
  Debug logs: <paste relevant lines>

Test B (close-up): 
  Reason: "<actual message>"
  Status: accepted/rejected
  Hairline: <result> (conf: X.XX)
  Jawline: <result> (conf: X.XX)

Test C (no person):
  Reason: "<actual message>"
  Status: accepted/rejected

Test D (multiple):
  Reason: "<actual message>"
  Status: accepted/rejected

Test E (turned head):
  Reason: "<actual message>"
  Status: accepted/rejected
```
