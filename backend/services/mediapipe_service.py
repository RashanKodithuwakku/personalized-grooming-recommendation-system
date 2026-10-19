import cv2
import numpy as np
import mediapipe as mp


class MediaPipeService:
    """
    Service for MediaPipe Face Mesh processing, pose validation (pitch, yaw, roll),
    and facial tabular feature extraction for XGBoost classifier models.
    """

    def __init__(
        self,
        static_image_mode: bool = True,
        max_num_faces: int = 1,
        refine_landmarks: bool = True,
        min_detection_confidence: float = 0.5,
        yaw_threshold: float = 15.0,
        pitch_threshold: float = 15.0,
        roll_threshold: float = 15.0
    ):
        self.yaw_threshold = yaw_threshold
        self.pitch_threshold = pitch_threshold
        self.roll_threshold = roll_threshold

        # Initialize mp.solutions.face_mesh in the constructor
        self.mp_solutions = getattr(mp, "solutions", None)
        if self.mp_solutions and hasattr(self.mp_solutions, "face_mesh"):
            self.mp_face_mesh = self.mp_solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=static_image_mode,
                max_num_faces=max_num_faces,
                refine_landmarks=refine_landmarks,
                min_detection_confidence=min_detection_confidence
            )
        else:
            self.mp_face_mesh = None
            self.face_mesh = None

    def validate_and_extract_landmarks(self, cv2_image: np.ndarray) -> dict:
        """
        Processes an OpenCV image (NumPy array) through MediaPipe Face Mesh.

        Checks performed:
        1. Face Detection: Returns {"is_valid": False, "reason": "No face detected"} if no face found.
        2. Pose Validation: Rejects if pitch, yaw, or roll exceed thresholds.
        3. Feature Extraction: Calculates tabular features (angles/ratios of jawline & facial structure).

        Returns:
            dict: {"is_valid": False, "reason": "..."} OR
                  {"is_valid": True, "features": [...], "reason": "Valid face"}
        """
        try:
            if cv2_image is None or not isinstance(cv2_image, np.ndarray) or cv2_image.size == 0:
                return {
                    "is_valid": False,
                    "reason": "Invalid or empty OpenCV image provided."
                }

            # Convert BGR OpenCV image to RGB for MediaPipe
            rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)

            landmarks = None

            if self.face_mesh is not None:
                results = self.face_mesh.process(rgb_image)
                if results and results.multi_face_landmarks:
                    landmarks = results.multi_face_landmarks[0].landmark

            # If no face is found, return validation failure
            if landmarks is None:
                return {
                    "is_valid": False,
                    "reason": "No face detected"
                }

            # Pose Validation: Calculate Pitch, Yaw, and Roll
            pitch, yaw, roll = self._estimate_pose_angles(landmarks)

            if abs(yaw) > self.yaw_threshold or abs(pitch) > self.pitch_threshold or abs(roll) > self.roll_threshold:
                return {
                    "is_valid": False,
                    "reason": "Face must be directly looking at the camera"
                }

            # Extract tabular features (angles/ratios of the jawline and face) for XGBoost model
            features = self._extract_tabular_features(landmarks)

            return {
                "is_valid": True,
                "features": features,
                "reason": "Valid face"
            }

        except Exception as e:
            return {
                "is_valid": False,
                "reason": f"MediaPipe face mesh processing error: {str(e)}"
            }

    def _estimate_pose_angles(self, landmarks) -> tuple:
        """
        Estimates Pitch, Yaw, and Roll pose angles in degrees using 3D facial landmarks.
        Reference Landmarks:
          33: Left eye outer corner
          263: Right eye outer corner
          10: Forehead top / hairline center
          152: Chin tip
        """
        l_eye = landmarks[33]
        r_eye = landmarks[263]
        forehead = landmarks[10]
        chin = landmarks[152]

        # Roll: rotation around Z-axis (head tilt side to side)
        dx_eye = r_eye.x - l_eye.x
        dy_eye = r_eye.y - l_eye.y
        roll = np.degrees(np.arctan2(dy_eye, dx_eye))

        # Yaw: rotation around Y-axis (head turn left to right)
        dz_eye = r_eye.z - l_eye.z
        yaw = np.degrees(np.arctan2(dz_eye, dx_eye))

        # Pitch: rotation around X-axis (head tilt up or down)
        dy_face = chin.y - forehead.y
        dz_face = chin.z - forehead.z
        pitch = np.degrees(np.arctan2(dz_face, dy_face))

        return float(pitch), float(yaw), float(roll)

    def _extract_tabular_features(self, landmarks) -> list:
        """
        Calculates geometric facial and jawline ratios & angles to construct
        tabular features for XGBoost profile classification.
        """
        def dist(p1, p2):
            return np.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2)

        def angle(p1, vertex, p2):
            v1 = np.array([p1.x - vertex.x, p1.y - vertex.y, p1.z - vertex.z])
            v2 = np.array([p2.x - vertex.x, p2.y - vertex.y, p2.z - vertex.z])
            norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            cos_theta = np.dot(v1, v2) / (norm1 * norm2)
            return float(np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0))))

        # Landmark points
        forehead = landmarks[10]
        chin = landmarks[152]
        nose = landmarks[1]
        l_jaw = landmarks[172]
        r_jaw = landmarks[397]
        l_cheek = landmarks[234]
        r_cheek = landmarks[454]
        l_temple = landmarks[54]
        r_temple = landmarks[284]
        l_eye = landmarks[33]
        r_eye = landmarks[263]

        face_height = dist(forehead, chin) + 1e-6
        jaw_width = dist(l_jaw, r_jaw)
        cheek_width = dist(l_cheek, r_cheek)
        forehead_width = dist(l_temple, r_temple)
        interocular_dist = dist(l_eye, r_eye)

        f1 = jaw_width / face_height                   # Jaw width to face height ratio
        f2 = cheek_width / face_height                 # Face width to height ratio
        f3 = cheek_width / (jaw_width + 1e-6)          # Cheek width to jaw width ratio
        f4 = forehead_width / (jaw_width + 1e-6)       # Forehead width to jaw width ratio
        f5 = angle(l_jaw, chin, r_jaw)                 # Chin jawline angle (degrees)
        f6 = dist(nose, chin) / face_height            # Lower face height ratio
        f7 = angle(l_cheek, l_jaw, chin)               # Left jawline corner angle
        f8 = angle(r_cheek, r_jaw, chin)               # Right jawline corner angle
        f9 = interocular_dist / (cheek_width + 1e-6)   # Interocular distance ratio
        f10 = dist(forehead, nose) / face_height       # Upper face height ratio

        return [
            float(f1), float(f2), float(f3), float(f4), float(f5),
            float(f6), float(f7), float(f8), float(f9), float(f10)
        ]
