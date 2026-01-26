from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import date
import hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = "supersecretkey123"

# ---------- تنظیمات ----------
DATABASE_PATH = "database/library.db"
UPLOAD_FOLDER = "static/photos"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs("database", exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------- دیتابیس ----------
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- ادمین ----------
def init_admin():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    admin = conn.execute("SELECT * FROM admins WHERE username='admin'").fetchone()
    if not admin:
        hashed = hashlib.sha256("1234".encode()).hexdigest()
        conn.execute(
            "INSERT INTO admins (username, password) VALUES (?, ?)",
            ("admin", hashed)
        )
    conn.commit()
    conn.close()

# ---------- جدول‌های اعضا، کتاب‌ها، امانت ----------
def init_tables():
    conn = get_db_connection()
    # اعضا
    conn.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            code TEXT UNIQUE,
            grade TEXT,
            phone TEXT,
            photo TEXT
        )
    """)
    # کتاب‌ها
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            subject TEXT,
            shelf TEXT,
            status TEXT
        )
    """)
    # امانت‌ها
    conn.execute("""
        CREATE TABLE IF NOT EXISTS borrowings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            book_id INTEGER,
            borrow_date TEXT,
            return_date TEXT,
            status TEXT,
            FOREIGN KEY(member_id) REFERENCES members(id),
            FOREIGN KEY(book_id) REFERENCES books(id)
        )
    """)
    conn.commit()
    conn.close()

init_admin()
init_tables()

# ---------- محافظ ----------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

# ---------- لاگین ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        conn = get_db_connection()
        admin = conn.execute(
            "SELECT * FROM admins WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()
        if admin:
            session["admin_logged_in"] = True
            return redirect("/dashboard")
        return render_template("login.html", error="اطلاعات اشتباه است")
    return render_template("login.html", error=None)

@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect("/login")

@app.route("/")
def index():
    return redirect("/login")

# ---------- داشبورد ----------
@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    members_count = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    books_count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    borrowed_count = conn.execute("SELECT COUNT(*) FROM books WHERE status='امانت'").fetchone()[0]
    free_count = conn.execute("SELECT COUNT(*) FROM books WHERE status='آزاد'").fetchone()[0]

    today_borrows = conn.execute("SELECT COUNT(*) FROM borrowings WHERE borrow_date=?", (date.today().isoformat(),)).fetchone()[0]
    active_borrows = conn.execute("SELECT COUNT(*) FROM borrowings WHERE status='امانت'").fetchone()[0]

    top_member = conn.execute("""
        SELECT members.name, COUNT(*) as total
        FROM borrowings
        JOIN members ON borrowings.member_id = members.id
        GROUP BY member_id
        ORDER BY total DESC
        LIMIT 1
    """).fetchone()

    top_book = conn.execute("""
        SELECT books.title, COUNT(*) as total
        FROM borrowings
        JOIN books ON borrowings.book_id = books.id
        GROUP BY book_id
        ORDER BY total DESC
        LIMIT 1
    """).fetchone()
    conn.close()

    return render_template(
        "dashboard.html",
        members_count=members_count,
        books_count=books_count,
        borrowed_count=borrowed_count,
        free_count=free_count,
        today_borrows=today_borrows,
        active_borrows=active_borrows,
        top_member=top_member,
        top_book=top_book
    )

# ---------- اعضا ----------
@app.route("/members")
@login_required
def members():
    conn = get_db_connection()
    members = conn.execute("SELECT * FROM members").fetchall()
    conn.close()
    return render_template("members.html", members=members)

@app.route("/search_members")
@login_required
def search_members():
    q = request.args.get("q", "").strip()
    conn = get_db_connection()
    members = conn.execute("SELECT * FROM members WHERE name LIKE ? OR code LIKE ? OR phone LIKE ?", (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    conn.close()
    return render_template("members.html", members=members, search=q)

@app.route("/add_member", methods=["GET", "POST"])
@login_required
def add_member():
    if request.method == "POST":
        name = request.form["name"]
        code = request.form["code"]
        grade = request.form["grade"]
        phone = request.form["phone"]
        photo_file = request.files.get("photo")
        filename = None
        if photo_file and photo_file.filename:
            filename = secure_filename(photo_file.filename)
            photo_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        conn = get_db_connection()
        conn.execute("INSERT INTO members (name, code, grade, phone, photo) VALUES (?, ?, ?, ?, ?)",
                     (name, code, grade, phone, filename))
        conn.commit()
        conn.close()
        return redirect("/members")
    return render_template("add_member.html")

# ---------- ویرایش عضو ----------
@app.route("/edit_member/<int:member_id>", methods=["GET", "POST"])
@login_required
def edit_member(member_id):
    conn = get_db_connection()
    member = conn.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
    if request.method == "POST":
        name = request.form["name"]
        code = request.form["code"]
        grade = request.form["grade"]
        phone = request.form["phone"]
        photo_file = request.files.get("photo")
        filename = member["photo"]
        if photo_file and photo_file.filename:
            filename = secure_filename(photo_file.filename)
            photo_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        conn.execute("UPDATE members SET name=?, code=?, grade=?, phone=?, photo=? WHERE id=?",
                     (name, code, grade, phone, filename, member_id))
        conn.commit()
        conn.close()
        return redirect("/members")
    conn.close()
    return render_template("add_member.html", member=member)

# ---------- کتاب‌ها ----------
@app.route("/books")
@login_required
def books():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return render_template("books.html", books=books)

@app.route("/search_books")
@login_required
def search_books():
    q = request.args.get("q", "").strip()
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books WHERE title LIKE ? OR subject LIKE ? OR shelf LIKE ?",
                         (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    conn.close()
    return render_template("books.html", books=books, search=q)

@app.route("/add_book", methods=["GET", "POST"])
@login_required
def add_book():
    if request.method == "POST":
        conn = get_db_connection()
        conn.execute("INSERT INTO books (title, subject, shelf, status) VALUES (?, ?, ?, 'آزاد')",
                     (request.form["title"], request.form["subject"], request.form["shelf"]))
        conn.commit()
        conn.close()
        return redirect("/books")
    return render_template("add_book.html")

@app.route("/edit_book/<int:book_id>", methods=["GET", "POST"])
@login_required
def edit_book(book_id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if request.method == "POST":
        title = request.form["title"]
        subject = request.form["subject"]
        shelf = request.form["shelf"]
        conn.execute("UPDATE books SET title=?, subject=?, shelf=? WHERE id=?", (title, subject, shelf, book_id))
        conn.commit()
        conn.close()
        return redirect("/books")
    conn.close()
    return render_template("edit_book.html", book=book)

# ---------- امانت ----------
@app.route("/add_borrow_select")
@login_required
def add_borrow_select():
    conn = get_db_connection()
    members = conn.execute("SELECT * FROM members").fetchall()
    conn.close()
    return render_template("select_member.html", members=members)

@app.route("/add_borrow/<int:member_id>", methods=["GET", "POST"])
@login_required
def add_borrow(member_id):
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books WHERE status='آزاد'").fetchall()
    if request.method == "POST":
        book_id = request.form["book_id"]
        conn.execute("INSERT INTO borrowings (member_id, book_id, borrow_date, status) VALUES (?, ?, ?, 'امانت')",
                     (member_id, book_id, date.today().isoformat()))
        conn.execute("UPDATE books SET status='امانت' WHERE id=?", (book_id,))
        conn.commit()
        conn.close()
        return redirect("/members")
    conn.close()
    return render_template("add_borrow.html", books=books, member_id=member_id)

@app.route("/return_book/<int:borrow_id>/<int:book_id>")
@login_required
def return_book(borrow_id, book_id):
    conn = get_db_connection()
    conn.execute("UPDATE borrowings SET return_date=?, status='تحویل شده' WHERE id=?",
                 (date.today().isoformat(), borrow_id))
    conn.execute("UPDATE books SET status='آزاد' WHERE id=?", (book_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

# ---------- فیلتر کتاب‌ها ----------
@app.route("/borrowed_books")
@login_required
def borrowed_books():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books WHERE status='امانت'").fetchall()
    conn.close()
    return render_template("books.html", books=books)

@app.route("/free_books")
@login_required
def free_books():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books WHERE status='آزاد'").fetchall()
    conn.close()
    return render_template("books.html", books=books)

# ---------- اجرا ----------
if __name__ == "__main__":
    app.run(debug=True)
