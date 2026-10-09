import json
import numpy as np

def load_library():
    with open("templates/library.json") as f:
        return json.load(f)

def select_variant(user_face_width, user_hair_density, style_prefix, gender):
    library = load_library()  # mēka issara code eke næthi line eka
    
    candidates = {k: v for k, v in library.items() 
                  if k.startswith(style_prefix) and v["gender"] == gender}
    
    if not candidates:
        return None, None, None  # style/gender ekata match wena variant ekak næha nam
    
    best_variant = None
    best_distance = float("inf")
    
    for variant_name, data in candidates.items():
        variant_vec = np.array([data["face_width_ratio"], data["hair_density_score"]])
        user_vec = np.array([user_face_width, user_hair_density])
        distance = np.linalg.norm(user_vec - variant_vec)
        
        if distance < best_distance:
            best_distance = distance
            best_variant = variant_name
    
    return best_variant, best_distance, library[best_variant]