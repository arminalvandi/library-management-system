from flask import Flask, render_template, request, redirect
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ---------- تنظیمات ----------
DATABASE_PATH = "database/library.db"
UPLOAD_FOLDER = "static/photos"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------- ساخت پوشه‌ها ----------
if not os.path.exists("database"):
    os.makedirs("database")

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------- اتصال دیتابیس ----------
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- صفحه تست ----------
@app.route("/")
def index():
    return redirect("/members")

# ---------- لیست اعضا ----------
@app.route("/members")
def members():
    conn = get_db_connection()
    members = conn.execute("SELECT * FROM members").fetchall()
    conn.close()
    return render_template("members.html", members=members)

# ---------- ثبت عضو ----------
@app.route("/add_member", methods=["GET", "POST"])
def add_member():
    if request.method == "POST":
        name = request.form["name"]
        code = request.form["code"]
        grade = request.form["grade"]
        phone = request.form["phone"]

        photo = request.files["photo"]
        photo_filename = None

        if photo and photo.filename != "":
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

# ---------- اطلاعات دانش‌آموز ----------
@app.route("/member/<int:member_id>")
def member_detail(member_id):
    conn = get_db_connection()
    member = conn.execute(
        "SELECT * FROM members WHERE id = ?",
        (member_id,)
    ).fetchone()
    conn.close()
    return render_template("member_detail.html", member=member)

# ---------- اجرای برنامه ----------
if __name__ == "__main__":@app.route("/edit_member/<int:member_id>", methods=["GET", "POST"])
def edit_member(member_id):
    conn = get_db_connection()
    member = conn.execute(
        "SELECT * FROM members WHERE id = ?",
        (member_id,)
    ).fetchone()

    if request.method == "POST":
        name = request.form["name"]
        code = request.form["code"]
        grade = request.form["grade"]
        phone = request.form["phone"]

        photo = request.files["photo"]
        photo_filename = member["photo_path"]

        if photo and photo.filename != "":
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
    app.run(debug=True)
