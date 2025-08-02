from flask import Flask, redirect, render_template, request, url_for, session
import sqlite3
from dotenv import load_dotenv
import os

app = Flask(__name__)
load_dotenv()
app.secret_key = os.getenv('SECRET_KEY')

def init_db():
    conn = sqlite3.connect("Ramblr.db")
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            post TEXT DEFAULT ''
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Comments (
            comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            comment TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

@app.route("/")
def landing():
    return render_template('index.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect("Ramblr.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['name'] = user[1]
            return redirect(url_for('home'))
        else:
            return redirect(url_for('landing'))

    return render_template('login.html')

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect("Ramblr.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO Users (name, email, password) VALUES (?, ?, ?)",
                (name, email, password)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('signup.html', error="Email already exists.")
    return render_template('signup.html')

@app.route("/home", methods=['GET'])
def home():
    name = session.get('name')
    if not name:
        return redirect(url_for('login'))

    conn = sqlite3.connect('Ramblr.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, post FROM Topics ORDER BY id DESC")
    posts = cursor.fetchall()
    conn.close()

    return render_template('home.html', posts=posts, name=name)

@app.route("/post_details/<int:post_id>", methods=['GET', 'POST'])
def post_details(post_id):
    conn = sqlite3.connect('Ramblr.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Topics WHERE id = ?", (post_id,))
    post = cursor.fetchone()

    if not post:
        conn.close()
        return "Post not found", 404

    if request.method == 'POST':
        comment_text = request.form['comment']
        username = session.get('name')
        if username:
            cursor.execute(
                "INSERT INTO Comments (post_id, username, comment) VALUES (?, ?, ?)",
                (post_id, username, comment_text)
            )
            conn.commit()

    cursor.execute("SELECT * FROM Comments WHERE post_id = ?", (post_id,))
    comments = cursor.fetchall()
    conn.close()

    return render_template('post_details.html', post=post, comments=comments)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
