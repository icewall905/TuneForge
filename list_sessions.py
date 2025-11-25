import sqlite3
try:
    conn = sqlite3.connect('/opt/tuneforge/db/local_music.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM chat_sessions")
    rows = cursor.fetchall()
    print("Sessions:", rows)
    conn.close()
except Exception as e:
    print("Error:", e)
