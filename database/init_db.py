import sqlite3
import os

os.makedirs("database", exist_ok=True)

conn = sqlite3.connect("database/library.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    code TEXT,
    grade TEXT,
    phone TEXT,
    photo_path TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    subject TEXT,
    shelf TEXT,
    status TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS borrowings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER,
    book_id INTEGER,
    borrow_date TEXT,
    return_date TEXT,
    status TEXT
)
""")

conn.commit()
conn.close()

print("✅ دیتابیس ساخته شد")
