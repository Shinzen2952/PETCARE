import sqlite3

conn = sqlite3.connect("pets.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS adoptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    pet_name TEXT,
    pet_img TEXT,
    status TEXT DEFAULT 'Evaluating',
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')

conn.commit()
conn.close()
print("✅ Adoption table ready!")
