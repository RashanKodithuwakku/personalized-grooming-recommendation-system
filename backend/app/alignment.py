import cv2
import numpy as np

def align_variant(template_img, template_points, user_points):
    src = np.float32(template_points)
    dst = np.float32(user_points)
    
    matrix = cv2.getAffineTransform(src, dst)
    h, w = template_img.shape[:2]
    warped = cv2.warpAffine(template_img, matrix, (w, h))
    
    return warped

def fixed_overlay_baseline(template_img, target_size):
    return cv2.resize(template_img, target_size)