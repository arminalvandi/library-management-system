import sqlite3
import os

DATABASE_DIR = "database"
DATABASE_PATH = os.path.join(DATABASE_DIR, "library.db")
SCHEMA_PATH = os.path.join(DATABASE_DIR, "schema.sql")

if not os.path.exists(DATABASE_DIR):
    os.makedirs(DATABASE_DIR)

conn = sqlite3.connect(DATABASE_PATH)

with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    conn.executescript(f.read())

conn.commit()
conn.close()

print("✅ Database created successfully")
