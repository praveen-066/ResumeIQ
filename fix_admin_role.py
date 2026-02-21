import sqlite3

try:
    conn = sqlite3.connect('instance/resumeiq.db')
    cursor = conn.cursor()
    
    print("Updating admin role...")
    cursor.execute("UPDATE user SET role = 'admin' WHERE username = 'admin'")
    conn.commit()
    print("Role updated successfully.")
    
    print("Verifying update...")
    cursor.execute("SELECT id, username, role FROM user WHERE username = 'admin'")
    user = cursor.fetchone()
    if user:
        print(f"ID: {user[0]}, Username: {user[1]}, Role: {user[2]}")
    
    conn.close()

except Exception as e:
    print(f"Error: {e}")
