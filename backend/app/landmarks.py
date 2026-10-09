import cv2
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1)

def get_user_landmarks(image_path):
    image = cv2.imread(image_path)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_image)
    
    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0]
        h, w, _ = image.shape
        
        LEFT_JAW = 234
        RIGHT_JAW = 454
        FOREHEAD = 10
        
        points = [
            (int(landmarks.landmark[LEFT_JAW].x * w), int(landmarks.landmark[LEFT_JAW].y * h)),
            (int(landmarks.landmark[RIGHT_JAW].x * w), int(landmarks.landmark[RIGHT_JAW].y * h)),
            (int(landmarks.landmark[FOREHEAD].x * w), int(landmarks.landmark[FOREHEAD].y * h))
        ]
        return points
    return None

if __name__ == "__main__":
    points = get_user_landmarks("test_photos/user1.jpg")
    print("User landmarks:", points)