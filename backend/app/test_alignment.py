import cv2
from landmarks import get_user_landmarks
from selection import select_variant
from alignment import align_variant, fixed_overlay_baseline

# Step 1: User landmarks ganna
user_points = get_user_landmarks("test_photos/user1.jpg")
print("User points:", user_points)

if user_points is None:
    print("ERROR: No face detected in user1.jpg")
else:
    # Step 2: Variant select karanna (gender parameter eka add kara)
    variant_name, distance, variant_data = select_variant(
        user_face_width=0.72,
        user_hair_density=0.35,
        style_prefix="male_textured_crop",  # style prefix + gender name ekama
        gender="male"
    )
    print("Selected variant:", variant_name)
    
    # Step 3: Template load karanna (gender subfolder eka path ekata add kara)
    gender = variant_data["gender"]
    template_path = f"templates/{gender}/{variant_name}.jpg"
    template_img = cv2.imread(template_path)
    
    if template_img is None:
        print(f"ERROR: Could not load template at {template_path}")
    else:
        template_points = variant_data["points"]
        
        # Step 4: Align karanna
        warped, matrix = align_variant(template_img, template_points, user_points)
        baseline = fixed_overlay_baseline(template_img, (512, 512))
        
        # Step 5: Results save karanna
        cv2.imwrite("test_photos/warped_result.jpg", warped)
        cv2.imwrite("test_photos/baseline_result.jpg", baseline)
        print("Done - check test_photos folder")