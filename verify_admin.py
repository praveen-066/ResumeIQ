import requests
import re

BASE_URL = "http://127.0.0.1:5000"

def verify_admin_dashboard():
    session = requests.Session()
    
    # Login as admin
    login_url = f"{BASE_URL}/auth/login"
    login_data = {
        "username": "admin",
        "password": "password123"
    }
    try:
        response = session.post(login_url, json=login_data)
        if response.status_code != 200:
            print(f"Admin login failed: {response.status_code}")
            return
            
        # Access Admin Dashboard
        dashboard_url = f"{BASE_URL}/admin/"
        response = session.get(dashboard_url)
        
        if response.status_code == 200:
            print("Admin dashboard accessed successfully.")
            content = response.text
            
            # Check for new metric
            if "Avg Score" in content:
                print("Verified: Average Score metric is present.")
            else:
                print("Failed: Average Score metric not found.")
                
            # Check for Chart canvas
            if 'id="scoreChart"' in content:
                print("Verified: Chart canvas map is present.")
            else:
                print("Failed: Chart canvas not found.")
                
        else:
            print(f"Failed to access admin dashboard: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_admin_dashboard()
