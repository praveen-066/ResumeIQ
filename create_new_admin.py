import requests

BASE_URL = "http://127.0.0.1:5000"

def create_admin():
    print("Creating new Admin user...")
    # Register
    data = {
        "username": "admin",
        "email": "admin@gmail.com",
        "password": "password123"
    }
    try:
        res = requests.post(f"{BASE_URL}/auth/register", json=data)
        print(f"Register Status: {res.status_code}")
        print(res.text)
        
        # We need to manually update role to admin since register defaults to 'user'
        # But for now, we just want to ensure the app handles the request
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_admin()
