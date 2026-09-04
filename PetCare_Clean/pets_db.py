import sqlite3

conn = sqlite3.connect('pets.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS pets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    Age INTEGER NOT NULL,
    Date_Found TEXT NOT NULL,
    Characteristics TEXT,
    Information TEXT,
    img TEXT
)''')

conn.commit()
conn.close()
