import requests

BASE_URL = "http://127.0.0.1:5000"

def test_register():
    print("Testing Registration...")
    data = {
        "username": "naveen_fail", 
        "email": "fail@gmail.com"
        # "password": "naveen@123"  <-- Missing password
    }
    
    try:
        res = requests.post(f"{BASE_URL}/auth/register", json=data)
        print(f"Status Code: {res.status_code}")
        
        try:
            print("Trying to parse JSON...")
            print(res.json())
        except Exception as e:
            print("Failed to parse JSON. Response Text (First 500 chars):")
            print(res.text[:1000]) # Print first 1000 chars of HTML for traceback

    except Exception as e:
        print(f"Request Exception: {e}")

if __name__ == "__main__":
    test_register()
