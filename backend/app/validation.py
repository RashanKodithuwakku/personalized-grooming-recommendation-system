import numpy as np

def measure_error(predicted_points, true_points):
    """
    Calculate the average Euclidean distance between the two sets of points.
    """
    errors = [np.linalg.norm(np.array(p) - np.array(t)) 
              for p, t in zip(predicted_points, true_points)]
    return np.mean(errors)