"""
Quick test script for backend API
Usage: python test_backend.py <image_path>
"""
import sys
import requests

def test_analyze_face(image_path: str):
    """Test the /analyze_face endpoint"""
    url = "http://127.0.0.1:8000/analyze_face"
    
    print(f"Testing with image: {image_path}")
    print(f"POST {url}")
    print("-" * 50)
    
    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            response = requests.post(url, files=files)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        print(response.json())
        
    except FileNotFoundError:
        print(f"Error: Image file not found: {image_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_backend.py <image_path>")
        sys.exit(1)
    
    test_analyze_face(sys.argv[1])
