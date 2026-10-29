from landmarks import get_user_landmarks
from selection import select_variant
from alignment import align_variant, fixed_overlay_baseline, transform_points
from validation import measure_error
import cv2
import mediapipe as mp
from config import STANDARD_SIZE

mp_face_mesh = mp.solutions.face_mesh
face_mesh_extra = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1)

def get_extra_validation_point(image_path):
    """
    Alignment ekata use karanne nathi, venath point ekak (nose tip) ganna.
    Mēka, independent validation ekata use karanawa.
    """
    image = cv2.imread(image_path)
    image = cv2.resize(image, STANDARD_SIZE)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh_extra.process(rgb_image)
    
    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0]
        h, w, _ = image.shape
        NOSE_TIP = 1  # MediaPipe nose tip index eka
        point = (int(landmarks.landmark[NOSE_TIP].x * w), int(landmarks.landmark[NOSE_TIP].y * h))
        return point
    return None


test_users = ["test_photos/user1.jpg", "test_photos/user2.jpg", "test_photos/user3.jpg"]

results = []

for user_photo in test_users:
    user_points = get_user_landmarks(user_photo)
    if user_points is None:
        print(f"SKIP {user_photo}: no face detected")
        continue
    
    # Independent validation point ekak ganna (nose tip - alignment ekata use kale nehe)
    user_nose_point = get_extra_validation_point(user_photo)
    if user_nose_point is None:
        print(f"SKIP {user_photo}: no validation point")
        continue
    
    variant_name, _, variant_data = select_variant(
        user_face_width=0.72,
        user_hair_density=0.35,
        style_prefix="male_textured_crop",
        gender="male"
    )
    
    gender = variant_data["gender"]
    template_img = cv2.imread(f"templates/{gender}/{variant_name}.jpg")
    if template_img is None:
        print(f"SKIP {user_photo}: template not found")
        continue
    
    template_points = variant_data["points"]
    
    warped, matrix = align_variant(template_img, template_points, user_points)
    
    # Template eke nose point eka (manually estimate karala ganna ona, template points atharē average ekak)
    template_nose_estimate = [
        (template_points[0][0] + template_points[1][0]) / 2,
        (template_points[0][1] + template_points[1][1]) / 2 + 30  # approximate
    ]
    warped_nose_point = transform_points([template_nose_estimate], matrix)[0]
    
    # Dæn, REAL validation - warped nose point VS user ge real nose point
    geometry_error = measure_error([warped_nose_point], [user_nose_point])
    
    # Baseline: template eke (warp nathi) estimated nose point VS user ge real nose point
    baseline_error = measure_error([template_nose_estimate], [user_nose_point])
    
    results.append((user_photo, geometry_error, baseline_error))
    print(f"{user_photo}: Geometry error={geometry_error:.2f}px, Baseline error={baseline_error:.2f}px")

if results:
    avg_geo = sum(r[1] for r in results) / len(results)
    avg_base = sum(r[2] for r in results) / len(results)
    print(f"\n{'='*50}")
    print(f"Average Geometry-aware error: {avg_geo:.2f}px")
    print(f"Average Baseline error: {avg_base:.2f}px")
    print(f"Improvement: {avg_base - avg_geo:.2f}px better with geometry-aware method")
    print(f"{'='*50}")
else:
    print("No valid results - check face detection on test images")