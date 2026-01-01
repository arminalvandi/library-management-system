from flask import Flask
import sqlite3
import os

app = Flask(_name_)

DATABASE_PATH = "database/library.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    return "Library Management System Backend Ready"

if _name_ == "_main_":
    app.run(debug=True
