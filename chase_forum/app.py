from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed to use sessions

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users(username, password, email) VALUES(?,?,?)', (username, password, email))
        conn.commit()
        conn.close()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['username'] = username
            return redirect('/home')
        else:
            return "Invalid username or password. Try again."
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

@app.route('/post', methods=['GET', 'POST'])
def post():
    if 'username' not in session:
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        username = session['username']

        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO topics (username, title, content) VALUES (?, ?, ?)', (username, title, content))
        conn.commit()
        conn.close()

        return redirect('/home')
    return render_template('post.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    conn = sqlite3.connect('forum.db')
    cursor = conn.cursor()

    # Get all topics
    cursor.execute("SELECT * FROM topics ORDER BY id DESC")
    topics = cursor.fetchall()

    # Get all comments and group them by topic_id
    cursor.execute("SELECT topic_id, username, comment FROM comments")
    all_comments = cursor.fetchall()

    comments_dict = {}
    for topic_id, username, comment in all_comments:
        if topic_id not in comments_dict:
            comments_dict[topic_id] = []
        comments_dict[topic_id].append((username, comment))

    conn.close()

    return render_template('home.html', topics=topics, comments=comments_dict)

@app.route('/topic/<int:topic_id>', methods=['GET'])
def view_topic(topic_id):
    conn = sqlite3.connect('forum.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
    topic = cursor.fetchone()

    cursor.execute("SELECT * FROM comments WHERE topic_id = ?", (topic_id,))
    comments = cursor.fetchall()
    conn.close()

    return render_template('topic_detail.html', topic=topic, comments=comments)

@app.route('/comment/<int:topic_id>', methods=['POST'])
def comment(topic_id):
    if 'username' not in session:
        return redirect('/login')

    comment_text = request.form['comment']
    username = session['username']

    conn = sqlite3.connect('forum.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO comments (topic_id, username, comment) VALUES (?, ?, ?)', (topic_id, username, comment_text))
    conn.commit()
    conn.close()

    return redirect('/home')

@app.route('/')
def landingPage():
    return render_template('landingPage.html')

def init_db():
    conn = sqlite3.connect('forum.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL,
                        email TEXT NOT NULL)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS topics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT,
                        title TEXT,
                        content TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS comments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        topic_id INTEGER,
                        username TEXT,
                        comment TEXT,
                        FOREIGN KEY (topic_id) REFERENCES topics(id))''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)


