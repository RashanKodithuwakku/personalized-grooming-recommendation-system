from selection import select_variant

# Male test
variant, distance, data = select_variant(
    user_face_width=0.70, 
    user_hair_density=0.5, 
    style_prefix="male_textured_crop", 
    gender="male"
)
print(f"Male test — Selected: {variant}, Distance: {distance}")

# Female test
variant, distance, data = select_variant(
    user_face_width=0.72, 
    user_hair_density=0.6, 
    style_prefix="female_long_layered", 
    gender="female"
)
print(f"Female test — Selected: {variant}, Distance: {distance}")

# Beard test (male only — female ekata beard category eka næha)
variant, distance, data = select_variant(
    user_face_width=0.75, 
    user_hair_density=0.4, 
    style_prefix="male_short_beard", 
    gender="male"
)
print(f"Beard test — Selected: {variant}, Distance: {distance}")