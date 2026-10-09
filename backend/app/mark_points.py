import cv2
import os
import json

points = []

def click_event(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(points) >= 3:
            print("Already have 3 points! Press 'r' to reset, or any key to continue.")
            return
        
        points.append((x, y))
        point_number = len(points)
        
        cv2.circle(img, (x, y), 6, (0, 255, 0), -1)
        cv2.putText(img, str(point_number), (x + 10, y - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.imshow("image", img)
        
        labels = ["Left Jaw", "Right Jaw", "Forehead Top"]
        print(f"Point {point_number} ({labels[point_number-1]}): ({x}, {y})")
        
        if point_number == 3:
            print("All 3 points marked! Press 'r' to redo, or any other key for NEXT image.")

def reset_points():
    global points, img, current_image_path
    points = []
    img = cv2.imread(current_image_path)
    cv2.imshow("image", img)
    print("Points reset. Click again: 1) Left Jaw, 2) Right Jaw, 3) Forehead Top")

# ============================================
# SETTINGS
# ============================================
folders = ["templates/male", "templates/female"]
output_file = "templates/points_raw.json"

# ============================================
# ALREADY SAVED POINTS EKA LOAD KARANNA (thiyenawa nam)
# ============================================
if os.path.exists(output_file):
    with open(output_file, "r") as f:
        all_results = json.load(f)
    print(f"Loaded existing points for {len(all_results)} images from {output_file}")
else:
    all_results = {}
    print("No existing points file found - starting fresh")

# ============================================
# OKKOMA IMAGE FILES EKA, FOLDERS DEKAEN GANNA
# ============================================
all_image_files = []
for folder in folders:
    for filename in os.listdir(folder):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            key_name = os.path.splitext(filename)[0]
            full_path = os.path.join(folder, filename)
            all_image_files.append((key_name, full_path))

print(f"\nFound {len(all_image_files)} total images in folders")

# ============================================
# POINTS NÆTHI IMAGES WITHARAK FILTER KARANNA
# (already thiyena ewa skip karanawa, automatically)
# ============================================
images_to_mark = []
for key_name, full_path in all_image_files:
    if key_name not in all_results or not all_results[key_name].get("points"):
        images_to_mark.append((key_name, full_path))

print(f"Already have points for: {len(all_image_files) - len(images_to_mark)} images")
print(f"Need to mark points for: {len(images_to_mark)} images")
print("=" * 50)

if len(images_to_mark) == 0:
    print("All images already have points! Nothing to do.")
else:
    # ============================================
    # MISSING IMAGES WITHARAK, ONE BY ONE MARK KARANNA
    # ============================================
    for idx, (key_name, full_path) in enumerate(images_to_mark):
        current_image_path = full_path
        points = []
        
        img = cv2.imread(current_image_path)
        if img is None:
            print(f"SKIP: Could not load {current_image_path}")
            continue
        
        cv2.imshow("image", img)
        cv2.setMouseCallback("image", click_event)
        
        print(f"\n[{idx+1}/{len(images_to_mark)}] Image: {current_image_path}")
        print("Click IN ORDER: 1) Left Jaw  2) Right Jaw  3) Forehead Top")
        print("Press 'r' to reset this image")
        
        while True:
            key = cv2.waitKey(0) & 0xFF
            if key == ord('r'):
                reset_points()
            else:
                break
        
        cv2.destroyAllWindows()
        
        all_results[key_name] = {
            "points": points,
            "image_path": current_image_path
        }
        
        # HAMA IMAGE EKAKATAMA PASSE, IMMEDIATELY SAVE KARANAWA
        # (eken, mැda eke stop unath, data eka save wela thiyenawa)
        with open(output_file, "w") as f:
            json.dump(all_results, f, indent=2)
        
        print(f"Saved points for {key_name}")

print("\n" + "=" * 50)
print(f"DONE! Total images with points: {len(all_results)}")
print(f"All points saved to {output_file}")
print("=" * 50)