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
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    admin = conn.execute("SELECT * FROM users WHERE username='admin'").fetchone()
    if not admin:
        hashed = hashlib.sha256("1234".encode()).hexdigest()
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("admin", hashed)
        )
    conn.commit()
    conn.close()

# ---------- جدول‌ها ----------
def init_tables():
    conn = get_db_connection()
    # اعضا
    conn.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            student_code TEXT UNIQUE,
            grade TEXT,
            phone TEXT,
            photo_path TEXT,
            status TEXT DEFAULT 'active',
            is_deleted INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # کتاب‌ها
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            category TEXT,
            status TEXT DEFAULT 'آزاد',
            is_deleted INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # امانت‌ها
    conn.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            loan_date DATE DEFAULT CURRENT_DATE,
            return_date DATE,
            status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id),
            FOREIGN KEY (book_id) REFERENCES books(id)
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
        password_hash = hashlib.sha256(request.form["password"].encode()).hexdigest()
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username, password_hash)).fetchone()
        conn.close()
        if user:
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
    members_count = conn.execute("SELECT COUNT(*) FROM members WHERE is_deleted=0").fetchone()[0]
    books_count = conn.execute("SELECT COUNT(*) FROM books WHERE is_deleted=0").fetchone()[0]
    borrowed_count = conn.execute("SELECT COUNT(*) FROM loans WHERE status='active'").fetchone()[0]
    free_count = books_count - borrowed_count

    today_borrows = conn.execute("SELECT COUNT(*) FROM loans WHERE loan_date=?", (date.today().isoformat(),)).fetchone()[0]
    active_borrows = borrowed_count

    top_member = conn.execute("""
        SELECT members.full_name, COUNT(*) as total
        FROM loans
        JOIN members ON loans.member_id = members.id
        WHERE members.is_deleted=0
        GROUP BY member_id
        ORDER BY total DESC
        LIMIT 1
    """).fetchone()

    top_book = conn.execute("""
        SELECT books.title, COUNT(*) as total
        FROM loans
        JOIN books ON loans.book_id = books.id
        WHERE books.is_deleted=0
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
    members = conn.execute("SELECT * FROM members WHERE is_deleted=0").fetchall()
    conn.close()
    return render_template("members.html", members=members)

@app.route("/search_members")
@login_required
def search_members():
    q = request.args.get("q", "").strip()
    conn = get_db_connection()
    members = conn.execute("SELECT * FROM members WHERE (full_name LIKE ? OR student_code LIKE ? OR phone LIKE ?) AND is_deleted=0",
                           (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    conn.close()
    return render_template("members.html", members=members, search=q)

@app.route("/add_member", methods=["GET", "POST"])
@login_required
def add_member():
    if request.method == "POST":
        full_name = request.form["name"]
        student_code = request.form["code"]
        grade = request.form["grade"]
        phone = request.form["phone"]
        photo_file = request.files.get("photo")
        filename = None
        if photo_file and photo_file.filename:
            filename = secure_filename(photo_file.filename)
            photo_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        conn = get_db_connection()
        conn.execute("INSERT INTO members (full_name, student_code, grade, phone, photo_path) VALUES (?, ?, ?, ?, ?)",
                     (full_name, student_code, grade, phone, filename))
        conn.commit()
        conn.close()
        return redirect("/members")
    return render_template("add_member.html")

@app.route("/edit_member/<int:member_id>", methods=["GET", "POST"])
@login_required
def edit_member(member_id):
    conn = get_db_connection()
    member = conn.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
    if request.method == "POST":
        full_name = request.form["name"]
        student_code = request.form["code"]
        grade = request.form["grade"]
        phone = request.form["phone"]
        photo_file = request.files.get("photo")
        filename = member["photo_path"]
        if photo_file and photo_file.filename:
            filename = secure_filename(photo_file.filename)
            photo_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        conn.execute("UPDATE members SET full_name=?, student_code=?, grade=?, phone=?, photo_path=? WHERE id=?",
                     (full_name, student_code, grade, phone, filename, member_id))
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
    books = conn.execute("SELECT * FROM books WHERE is_deleted=0").fetchall()
    conn.close()
    return render_template("books.html", books=books)

@app.route("/search_books")
@login_required
def search_books():
    q = request.args.get("q", "").strip()
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books WHERE (title LIKE ? OR author LIKE ? OR category LIKE ?) AND is_deleted=0",
                         (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    conn.close()
    return render_template("books.html", books=books, search=q)

@app.route("/add_book", methods=["GET", "POST"])
@login_required
def add_book():
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["subject"]
        category = request.form["shelf"]
        conn = get_db_connection()
        conn.execute("INSERT INTO books (title, author, category, status) VALUES (?, ?, ?, 'آزاد')",
                     (title, author, category))
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
        author = request.form["subject"]
        category = request.form["shelf"]
        conn.execute("UPDATE books SET title=?, author=?, category=? WHERE id=?", (title, author, category, book_id))
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
    members = conn.execute("SELECT * FROM members WHERE is_deleted=0").fetchall()
    conn.close()
    return render_template("select_member.html", members=members)

@app.route("/add_borrow/<int:member_id>", methods=["GET", "POST"])
@login_required
def add_borrow(member_id):
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books WHERE status='آزاد' AND is_deleted=0").fetchall()
    if request.method == "POST":
        book_id = request.form["book_id"]
        conn.execute("INSERT INTO loans (member_id, book_id, loan_date, status) VALUES (?, ?, ?, 'active')",
                     (member_id, book_id, date.today().isoformat()))
        conn.execute("UPDATE books SET status='امانت' WHERE id=?", (book_id,))
        conn.commit()
        conn.close()
        return redirect("/members")
    conn.close()
    return render_template("add_borrow.html", books=books, member_id=member_id)

@app.route("/return_book/<int:loan_id>/<int:book_id>")
@login_required
def return_book(loan_id, book_id):
    conn = get_db_connection()
    conn.execute("UPDATE loans SET return_date=?, status='returned' WHERE id=?", (date.today().isoformat(), loan_id))
    conn.execute("UPDATE books SET status='آزاد' WHERE id=?", (book_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

@app.route("/borrowed_books")
@login_required
def borrowed_books():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books WHERE status='امانت' AND is_deleted=0").fetchall()
    conn.close()
    return render_template("books.html", books=books)

@app.route("/free_books")
@login_required
def free_books():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books WHERE status='آزاد' AND is_deleted=0").fetchall()
    conn.close()
    return render_template("books.html", books=books)

# ---------- اجرا ----------
if __name__ == "__main__":
    app.run(debug=True)
