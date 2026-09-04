import sqlite3

conn = sqlite3.connect("pets.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS adoptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    pet_name TEXT,
    pet_img TEXT,
    status TEXT
);
""")

conn.commit()
conn.close()

print("✅ Table 'adoptions' created successfully in pets.db!")
