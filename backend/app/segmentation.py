import cv2
import numpy as np
import torch
import sys
import torchvision.transforms as transforms
from PIL import Image

# BiSeNet repository eka point karanna
sys.path.append('../face-parsing.PyTorch')
from model import BiSeNet

def load_bisenet_model(weight_path):
    model = BiSeNet(n_classes=19)
    model.load_state_dict(torch.load(weight_path, map_location='cpu'))
    model.eval()
    return model

# Normalize transform eka, test.py ekema use kala eka ekamama
to_tensor = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
])

def get_hair_mask(model, image_path):
    img = cv2.imread(image_path)
    original_height, original_width = img.shape[:2]
    
    img_resized = cv2.resize(img, (512, 512))
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    
    # PIL Image ekata convert karanna ona, to_tensor transform eka wada karanna
    pil_image = Image.fromarray(img_rgb)
    img_tensor = to_tensor(pil_image)
    img_tensor = img_tensor.unsqueeze(0)
    
    with torch.no_grad():
        output = model(img_tensor)[0]
        parsing = output.squeeze(0).cpu().numpy().argmax(0)
    
    print("Unique classes detected:", np.unique(parsing))
    
    HAIR_CLASS_ID = 17
    hair_pixel_count = np.sum(parsing == HAIR_CLASS_ID)
    print("Hair pixels found (before cleanup):", hair_pixel_count)
    
    hair_mask = (parsing == HAIR_CLASS_ID).astype('uint8') * 255
    
    # ============================================
    # ALUTH STEP — Morphological Closing
    # Small gaps/holes tika, hair region eka athule, fill karanawa
    # ============================================
    kernel = np.ones((9, 9), np.uint8)
    hair_mask = cv2.morphologyEx(hair_mask, cv2.MORPH_CLOSE, kernel)
    
    hair_pixel_count_after = np.sum(hair_mask == 255)
    print("Hair pixels found (after cleanup):", hair_pixel_count_after)
    
    # Nearest-neighbor interpolation eka use karanawa, mask eka blur wenna epa
    hair_mask_resized = cv2.resize(
        hair_mask, 
        (original_width, original_height), 
        interpolation=cv2.INTER_NEAREST
    )
    
    return hair_mask_resized


if __name__ == "__main__":
    model = load_bisenet_model("../face-parsing.PyTorch/res/cp/79999_iter.pth")
    mask = get_hair_mask(model, "test_photos/user1.jpg")
    cv2.imwrite("test_photos/hair_mask_output.jpg", mask)
    print("Hair mask saved to test_photos/hair_mask_output.jpg")