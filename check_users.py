import sqlite3

try:
    conn = sqlite3.connect('instance/resumeiq.db')
    cursor = conn.cursor()
    
    print("Checking users in database...")
    cursor.execute("SELECT id, username, role FROM user")
    users = cursor.fetchall()
    
    for user in users:
        print(f"ID: {user[0]}, Username: {user[1]}, Role: {user[2]}")
        
    conn.close()

except Exception as e:
    print(f"Error: {e}")
