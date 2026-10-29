# Component 3 ready wenakan, mock data ekak use karanawa
# Dæn, hairstyle saha beard, VENAS VENAS RANKED LISTS widiyata organize kara

MOCK_RANKED_STYLES_MALE = {
    "hairstyle": [
        {"style": "male_textured_crop", "confidence": 0.87, "rank": 1},
        {"style": "male_side_part", "confidence": 0.78, "rank": 2},
        {"style": "male_crew_cut", "confidence": 0.70, "rank": 3},
        {"style": "male_curly_top", "confidence": 0.65, "rank": 4},
    ],
    "beard": [
        {"style": "male_short_beard", "confidence": 0.82, "rank": 1},
        {"style": "male_full_beard", "confidence": 0.74, "rank": 2},
        {"style": "male_short_stubble", "confidence": 0.69, "rank": 3},
    ]
}

MOCK_RANKED_STYLES_FEMALE = {
    "hairstyle": [
        {"style": "female_long_layered", "confidence": 0.84, "rank": 1},
        {"style": "female_bob_cut", "confidence": 0.76, "rank": 2},
        {"style": "female_curly_layered", "confidence": 0.71, "rank": 3},
        {"style": "female_pixie_cut", "confidence": 0.65, "rank": 4},
    ],
    "beard": []  # Female ekata beard category eka næha
}


def get_ranked_styles(gender, style_type):
    """
    Gender saha style_type (hairstyle/beard) anuwa, correct mock style list eka return karanawa.
    """
    if gender == "male":
        return MOCK_RANKED_STYLES_MALE.get(style_type, [])
    elif gender == "female":
        return MOCK_RANKED_STYLES_FEMALE.get(style_type, [])
    return []


def get_next_style(current_rank, gender, style_type):
    """
    Dislike dunnahama, SAME category ekema (hairstyle or beard), next rank eka ganna.
    """
    styles = get_ranked_styles(gender, style_type)
    for style in styles:
        if style["rank"] == current_rank + 1:
            return style
    return None  # No more styles in this category