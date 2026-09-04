import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    contact TEXT,
    birthdate TEXT,
    age INTEGER,
    address TEXT,
    valid_id_type TEXT,
    valid_id_path TEXT
);
""")

conn.commit()
conn.close()
print("✅ users table created successfully in users.db")
