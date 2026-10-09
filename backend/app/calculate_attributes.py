import cv2
import numpy as np
import json
import math

def calculate_face_width_ratio(points, image_width):
    """
    Euclidean distance formula use karala, left jaw saha right jaw 
    points dekē atharē actual pixel distance eka calculate karanawa,
    image width ekata normalize karala.
    """
    left_jaw = points[0]
    right_jaw = points[1]
    
    # Euclidean distance (Pythagorean theorem)
    jaw_distance = math.sqrt(
        (right_jaw[0] - left_jaw[0]) ** 2 + 
        (right_jaw[1] - left_jaw[1]) ** 2
    )
    
    # Image width ekata relative karala, ratio ekak widiyata denawa (0.0 - 1.0 range)
    ratio = jaw_distance / image_width
    
    return round(ratio, 3)


def calculate_hair_density(image_path, points, image_width, image_height):
    """
    Forehead point eka udin, hair region ekak approximate karala,
    standard deviation of pixel intensity (texture complexity) 
    calculate karanawa. Ihala std dev = curly/textured hair (vedi variation),
    adui std dev = straight/short hair (adui variation).
    """
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    forehead_point = points[2]  # 3rd point eka, forehead top
    fx, fy = forehead_point
    
    # Forehead point ekata uda, hair region ekak approximate karanawa
    # (box ekak, forehead eken udata, head eke top ekata kiට)
    region_height = int(image_height * 0.25)  # image height eke 25%ak
    region_width = int(image_width * 0.4)     # image width eke 40%ak
    
    y_start = max(0, fy - region_height)
    y_end = fy
    x_start = max(0, fx - region_width // 2)
    x_end = min(image_width, fx + region_width // 2)
    
    hair_region = img[y_start:y_end, x_start:x_end]
    
    if hair_region.size == 0:
        return None
    
    # Grayscale ekata convert karala, standard deviation eka calculate karanawa
    gray_region = cv2.cvtColor(hair_region, cv2.COLOR_BGR2GRAY)
    std_dev = np.std(gray_region)
    
    # 0-255 range eka, 0.0-1.0 range ekata normalize karanawa
    density_score = std_dev / 128.0  # 128 ~ typical max std dev for texture
    density_score = min(density_score, 1.0)  # 1.0 ta vedi wenna epa
    
    return round(density_score, 3)


def process_library(library_path, image_base_width=512, image_base_height=512):
    with open(library_path, "r") as f:
        library = json.load(f)
    
    for key_name, data in library.items():
        points = data["points"]
        image_path = data.get("image_path", "").replace("\\", "/")
        
        if not image_path or not points or len(points) < 3:
            print(f"SKIP {key_name}: missing points or image path")
            continue
        
        # face_width_ratio calculate karanawa
        face_width_ratio = calculate_face_width_ratio(points, image_base_width)
        
        # hair_density_score calculate karanawa
        hair_density = calculate_hair_density(
            image_path, points, image_base_width, image_base_height
        )
        
        if hair_density is None:
            print(f"WARNING {key_name}: could not calculate hair density, keeping old value")
            continue
        
        # library dictionary eka update karanawa
        library[key_name]["face_width_ratio"] = face_width_ratio
        library[key_name]["hair_density_score"] = hair_density
        
        print(f"{key_name}: face_width_ratio={face_width_ratio}, hair_density_score={hair_density}")
    
    # Updated library eka, file ekatama save karanawa
    with open(library_path, "w") as f:
        json.dump(library, f, indent=2)
    
    print(f"\nDone! Updated {library_path} with calculated values.")


if __name__ == "__main__":
    process_library("templates/library.json")