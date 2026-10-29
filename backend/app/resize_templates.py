import cv2
import os
from config import STANDARD_SIZE

def resize_folder(folder_path, target_size=STANDARD_SIZE):
    for filename in os.listdir(folder_path):
        if filename.endswith((".jpg", ".png", ".jpeg")):
            path = os.path.join(folder_path, filename)
            img = cv2.imread(path)
            if img is not None:
                resized = cv2.resize(img, target_size)
                cv2.imwrite(path, resized)
                print(f"Resized: {filename}")

resize_folder("templates/male")
resize_folder("templates/female")