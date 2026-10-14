import cv2
from landmarks import get_user_landmarks
from selection import select_variant
from alignment import align_variant, fixed_overlay_baseline

# User landmarks ganna
user_points = get_user_landmarks("test_photos/user1.jpg")
print("User points:", user_points)

# Variant select karanna
variant_name, distance, variant_data = select_variant(0.72, 0.35, "textured_crop")
print("Selected variant:", variant_name)

# Template load karala align karanna
template_img = cv2.imread(f"templates/{variant_name}.jpg")
template_points = variant_data["points"]

warped = align_variant(template_img, template_points, user_points)
baseline = fixed_overlay_baseline(template_img, (512, 512))

cv2.imwrite("test_photos/warped_result.jpg", warped)
cv2.imwrite("test_photos/baseline_result.jpg", baseline)
print("Done - check test_photos folder")