import requests
import sys
import os

def test_analyze():
    url = "http://localhost:5500/api/v1/prescription/analyze"
    file_path = "tests/sample_prescription.png"
    
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"Sending request to {url} with {file_path}...")
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": ("prescription.png", f, "image/png")}
            response = requests.post(url, files=files)
            
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Response JSON:")
            print(data)
            
            medicines = data.get("medicines", [])
            print(f"\nFound {len(medicines)} medicines:")
            for med in medicines:
                print(f"- Name: {med['name']}")
                print(f"  Active Ingredient: {med['active_ingredient']}")
                print(f"  Image URL: {med['image_url']}")
        else:
            print("Error response:", response.text)

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_analyze()
