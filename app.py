    from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import date
import hashlib

app = Flask(__name__)
app.secret_key = "supersecretkey123"  # کلید امن برای session

# ---------- تنظیمات ----------
DATABASE_PATH = "database/library.db"
UPLOAD_FOLDER = "static/photos"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs("database", exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------- اتصال دیتابیس ----------
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- ایجاد جدول مدیر ----------
def init_admin():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    # اضافه کردن admin اولیه اگر وجود ندارد
    admin = conn.execute("SELECT * FROM admins WHERE username='admin'").fetchone()
    if not admin:
        hashed = hashlib.sha256("1234".encode()).hexdigest()
        conn.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ("admin", hashed))
    conn.commit()
    conn.close()

init_admin()

# ---------- صفحه ورود ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM admins WHERE username=? AND password=?", (username, hashed_password)).fetchone()
        conn.close()

        if admin:
            session["admin_logged_in"] = True
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="نام کاربری یا رمز عبور اشتباه است")

    return render_template("login.html", error=None)

# ---------- خروج ----------
@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect("/login")

# ---------- محافظت از صفحات ----------
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# ---------- صفحه اصلی ----------
@app.route("/")
def index():
    return redirect("/login")

# ---------- داشبورد مدیر ----------
@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    members_count = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    books_count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    borrowed_count = conn.execute("SELECT COUNT(*) FROM books WHERE status='امانت'").fetchone()[0]
    free_count = conn.execute("SELECT COUNT(*) FROM books WHERE status='آزاد'").fetchone()[0]
    conn.close()
    return render_template(
        "dashboard.html",
        members_count=members_count,
        books_count=books_count,
        borrowed_count=borrowed_count,
        free_count=free_count
    )

# ---------- اعضا ----------
@app.route("/members")
@login_required
def members():
    conn = get_db_connection()
    members = conn.execute("SELECT * FROM members").fetchall()
    conn.close()
    return render_template("members.html", members=members)

@app.route("/add_member", methods=["GET", "POST"])
@login_required
def add_member():
    if request.method == "POST":
        name = request.form["name"]
        code = request.form["code"]
        grade = request.form["grade"]
        phone = request.form["phone"]
        photo = request.files["photo"]
        photo_filename = None
        if photo and photo.filename:
            photo_filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], photo_filename))

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO members (name, code, grade, phone, photo_path)
            VALUES (?, ?, ?, ?, ?)
        """, (name, code, grade, phone, photo_filename))
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
        name = request.form["name"]
        code = request.form["code"]
        grade = request.form["grade"]
        phone = request.form["phone"]
        photo = request.files["photo"]
        photo_filename = member["photo_path"]
        if photo and photo.filename:
            photo_filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], photo_filename))

        conn.execute("""
            UPDATE members
            SET name=?, code=?, grade=?, phone=?, photo_path=?
            WHERE id=?
        """, (name, code, grade, phone, photo_filename, member_id))
        conn.commit()
        conn.close()
        return redirect("/members")
    conn.close()
    return render_template("edit_member.html", member=member)

@app.route("/member/<int:member_id>")
@login_required
def member_detail(member_id):
    conn = get_db_connection()
    member = conn.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
    borrows = conn.execute("""
        SELECT borrowings.id, books.title, borrow_date, return_date, status
        FROM borrowings
        JOIN books ON borrowings.book_id = books.id
        WHERE member_id=?
    """, (member_id,)).fetchall()
    conn.close()
    return render_template("member_detail.html", member=member, borrows=borrows)

# ---------- کتاب‌ها ----------
@app.route("/books")
@login_required
def books():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return render_template("books.html", books=books)

@app.route("/add_book", methods=["GET", "POST"])
@login_required
def add_book():
    if request.method == "POST":
        title = request.form["title"]
        subject = request.form["subject"]
        shelf = request.form["shelf"]

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO books (title, subject, shelf, status)
            VALUES (?, ?, ?, 'آزاد')
        """, (title, subject, shelf))
        conn.commit()
        conn.close()
        return redirect("/books")
    return render_template("add_book.html", book=None)

@app.route("/edit_book/<int:book_id>", methods=["GET", "POST"])
@login_required
def edit_book(book_id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if request.method == "POST":
        title = request.form["title"]
        subject = request.form["subject"]
        shelf = request.form["shelf"]
        conn.execute("""
            UPDATE books
            SET title=?, subject=?, shelf=?
            WHERE id=?
        """, (title, subject, shelf, book_id))
        conn.commit()
        conn.close()
        return redirect("/books")
    conn.close()
    return render_template("add_book.html", book=book)

# ---------- امانت ----------
@app.route("/add_borrow/<int:member_id>", methods=["GET", "POST"])
@login_required
def add_borrow(member_id):
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books WHERE status='آزاد'").fetchall()
    if request.method == "POST":
        book_id = request.form["book_id"]
        conn.execute("""
            INSERT INTO borrowings (member_id, book_id, borrow_date, status)
            VALUES (?, ?, ?, 'امانت')
        """, (member_id, book_id, date.today().isoformat()))
        conn.execute("UPDATE books SET status='امانت' WHERE id=?", (book_id,))
        conn.commit()
        conn.close()
        return redirect(url_for("member_detail", member_id=member_id))
    conn.close()
    return render_template("add_borrow.html", member_id=member_id, books=books)

@app.route("/return_book/<int:borrow_id>/<int:book_id>")
@login_required
def return_book(borrow_id, book_id):
    conn = get_db_connection()
    conn.execute("""
        UPDATE borrowings
        SET return_date=?, status='تحویل شده'
        WHERE id=?
    """, (date.today().isoformat(), borrow_id))
    conn.execute("UPDATE books SET status='آزاد' WHERE id=?", (book_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

# ---------- مسیر جدید: ثبت امانت برای همه اعضا و کتاب‌ها ----------
@app.route("/add_borrow_global", methods=["GET", "POST"])
@login_required
def add_borrow_global():
    conn = get_db_connection()
    members = conn.execute("SELECT * FROM members").fetchall()
    books = conn.execute("SELECT * FROM books WHERE status='آزاد'").fetchall()

    if request.method == "POST":
        member_id = request.form["member_id"]
        book_id = request.form["book_id"]

        conn.execute("""
            INSERT INTO borrowings (member_id, book_id, borrow_date, status)
            VALUES (?, ?, ?, 'امانت')
        """, (member_id, book_id, date.today().isoformat()))
        conn.execute("UPDATE books SET status='امانت' WHERE id=?", (book_id,))
        conn.commit()
        conn.close()
        return redirect("/dashboard")

    conn.close()
    return render_template("add_borrow_global.html", members=members, books=books)

# ---------- اجرا ----------
if __name__ == "__main__":
    app.run(debug=True)
