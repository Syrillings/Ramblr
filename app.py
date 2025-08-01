from flask import Flask, redirect, render_template, request, url_for, session
import sqlite3
app = Flask(__name__)
from dotenv import load_dotenv
import os

load_dotenv()
app.secret_key = os.getenv('SECRET_KEY') or 'default-very-secret-key-12345'

@app.route("/")
def landing():
    #This is supposed to be for the landing page
    return render_template('index.html')


def init_db():
    conn = sqlite3.connect("Ramblr.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            post TEXT DEFAULT '',
            comment TEXT DEFAULT '',
            comment_id INTEGER DEFAULT 0
            
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

    # Get all topics
    cursor.execute("SELECT id, post FROM Users ORDER BY id DESC")
    posts = cursor.fetchall()

    # Get all comments and group them by topic_id
   #REMEMBER LATER cursor.execute("SELECT topic_id, username, comment FROM comments")
    #all_comments = cursor.fetchall()

    ''' comments_dict = {}
    for topic_id, username, comment in all_comments:
        if topic_id not in comments_dict:
            comments_dict[topic_id] = []
        comments_dict[topic_id].append((username, comment))

    conn.close()
    '''
    return render_template('home.html', posts=posts, name=name)

# Comment logic starts here
def comment(id):
    if 'name' not in session:
        return redirect('/login')

    comment_text = request.form['comment']
    username = session['username']

    conn = sqlite3.connect('Ramblr.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Users (topic_id, comment) VALUES (?, ?)', (id, comment_text))
    conn.commit()
    conn.close()

    return redirect('/home')

@app.route("/post_details/<int:post_id>", methods=['GET', 'POST'])
def post_details(post_id):
    conn = sqlite3.connect('Ramblr.db')
    cursor = conn.cursor()

    # Get post details
    cursor.execute("SELECT * FROM Users WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    
    if not post:
        return "Post not found", 404

    # Get comments for the post
    cursor.execute("SELECT * FROM Users WHERE id = ?", (post_id,))
    comments = cursor.fetchall()

    if request.method == 'POST':
        comment_text = request.form['comment']
        username = session.get('name', 'Anonymous')
        cursor.execute('INSERT INTO Users (id, name, comment) VALUES (?, ?, ?)', (post_id, username, comment_text))
        conn.commit()

    conn.close()
    return render_template('post_details.html', post=post, comments=comments)


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
