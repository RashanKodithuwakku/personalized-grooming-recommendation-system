from main_flow import generate_preview, process_feedback, process_advanced_preview_choice
from database import init_db, get_all_feedback
from segmentation import load_bisenet_model

# Database eka initialize karanna
init_db()

# BiSeNet model eka, ekama paysak load karanawa
model = load_bisenet_model("../face-parsing.PyTorch/res/cp/79999_iter.pth")

# Step 1: First style eka preview karanna (rank 1)
result = generate_preview(
    user_id="test_user_1",
    user_photo_path="test_photos/user1.jpg",
    gender="male",
    current_rank=1,
    bisenet_model=model
)
print("Preview 1:", result)

# Step 2: User "dislike" dunna kiyala simulate karanna
feedback_result = process_feedback(
    user_id="test_user_1",
    current_rank=1,
    feedback_value="dislike",
    style_shown=result["style"],
    variant_shown=result["variant"],
    gender="male"
)
print("Feedback result:", feedback_result)

# Step 3: Dislike una nisa, next style eka (rank 2) preview karanna
if feedback_result["action"] == "show_next":
    next_rank = feedback_result["next_rank"]
    result2 = generate_preview(
        user_id="test_user_1",
        user_photo_path="test_photos/user1.jpg",
        gender="male",
        current_rank=next_rank,
        bisenet_model=model
    )
    print("Preview 2:", result2)
    
    # Step 4: Mē paya, user "like" dunna kiyala simulate karanna
    feedback_result2 = process_feedback(
        user_id="test_user_1",
        current_rank=next_rank,
        feedback_value="like",
        style_shown=result2["style"],
        variant_shown=result2["variant"],
        gender="male"
    )
    print("Feedback result 2:", feedback_result2)
    
    # Step 5: Like unoth, advanced preview ekak ona da kiyala ahanawa
    if feedback_result2["action"] == "ask_advanced_preview":
        advanced_choice = process_advanced_preview_choice(wants_advanced=False)  # test: "No" select kala
        print("Advanced preview choice:", advanced_choice)

# Database eke okkoma feedback records balanna
print("\nAll feedback in database:")
for record in get_all_feedback():
    print(record)