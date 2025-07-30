from flask import Flask, redirect, render_template, request, url_for
import sqlite3
app = Flask(__name__)


@app.route("/")
def landing():
    return render_template('index.html')


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
    conn.commit()
    conn.close()


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect("Ramblr.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM Users WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            name = user[1]
            return render_template('home.html', name=name)
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


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
