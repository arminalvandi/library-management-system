from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import date

app = Flask(__name__)

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

# ---------- صفحه اصلی ----------
@app.route("/")
def index():
    return redirect("/members")

# ---------- اعضا ----------
@app.route("/members")
def members():
    conn = get_db_connection()
    members = conn.execute("SELECT * FROM members").fetchall()
    conn.close()
    return render_template("members.html", members=members)

@app.route("/add_member", methods=["GET", "POST"])
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
def books():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return render_template("books.html", books=books)

@app.route("/add_book", methods=["GET", "POST"])
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

# ---------- اجرا ----------
if __name__ == "__main__":
    app.run(debug=True)
