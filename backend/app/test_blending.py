import cv2
from landmarks import get_user_landmarks
from selection import select_variant
from alignment import align_variant
from segmentation import load_bisenet_model, get_hair_mask
from blending import blend_template
from explanation import generate_explanation
from config import STANDARD_SIZE

# Step 1: User1 ge original photo eka load karanna, STANDARD_SIZE ekatama resize karanna
user_photo = cv2.imread("test_photos/user1.jpg")
user_photo = cv2.resize(user_photo, STANDARD_SIZE)

# Step 2: User landmarks ganna (gender/path dependency ekak næha, mēka already hari)
user_points = get_user_landmarks("test_photos/user1.jpg")

if user_points is None:
    print("ERROR: No face detected")
else:
    # Step 3: Variant select karanna (gender parameter eka ekathu)
    variant_name, distance, variant_data = select_variant(
        user_face_width=0.72,
        user_hair_density=0.35,
        style_prefix="male_textured_crop",
        gender="male"
    )
    
    # Step 4: Template load karanna (gender subfolder eka path ekata ekathu)
    gender = variant_data["gender"]
    template_img = cv2.imread(f"templates/{gender}/{variant_name}.jpg")
    
    if template_img is None:
        print(f"ERROR: Could not load template")
    else:
        template_points = variant_data["points"]
        
        # Step 5: Template eka, warp karanna (matrix eka return karanawa)
        warped, matrix = align_variant(template_img, template_points, user_points)
        
        # Step 6: User1 ge hair mask eka ganna (BiSeNet eken)
        model = load_bisenet_model("../face-parsing.PyTorch/res/cp/79999_iter.pth")
        hair_mask = get_hair_mask(model, "test_photos/user1.jpg")
        
        # Step 7: Blend karanna - warped template eka, user photo ekata merge karanawa
        center = (user_photo.shape[1] // 2, user_photo.shape[0] // 2)
        final_preview = blend_template(warped, user_photo, hair_mask, center)
        
        cv2.imwrite("test_photos/final_preview.jpg", final_preview)
        print("Final preview saved to test_photos/final_preview.jpg")
        
        # Step 8: Explanation eka generate karanna (Component 3 ge mock data use karala)
        mock_attribution_data = {
            "confidence": distance,  # ho, Component 3 eken real confidence eka
            "contributing_factors": {
                "jawline": 0.4,
                "forehead": 0.3,
                "symmetry": 0.3
            }
        }
        explanation_text = generate_explanation(mock_attribution_data)
        print("Explanation:", explanation_text)