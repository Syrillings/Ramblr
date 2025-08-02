from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

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
            session['user_id'] = user[0] 
            return redirect('/home')
        else:
            return "Invalid username or password. Try again."
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
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

@app.route('/home', methods=['GET'])
def home():
    conn = sqlite3.connect('forum.db')
    cursor = conn.cursor()

    # Get topics with like counts
    cursor.execute('''
        SELECT topics.id, topics.username, topics.title, topics.content,
               COUNT(likes.id) AS like_count
        FROM topics
        LEFT JOIN likes ON topics.id = likes.topic_id
        GROUP BY topics.id
        ORDER BY topics.id DESC
    ''')
    topics_raw = cursor.fetchall()
    user_liked_topic_ids = set()
    topics = []
    
    for topic in topics_raw:
        topic_id, username, title, content, like_count = topic
        truncated_content = content[:100] + '...' if len(content) > 40 else content
        liked_by_user = topic_id in user_liked_topic_ids

        topics.append({
            'id': topic_id,
            'username': username,
            'title': title,
            'truncated_content': truncated_content,
            'full_content': content,
            'likes': like_count,
            'liked_by_user': liked_by_user
        })

    # Get limited comments per topic
    cursor.execute("SELECT topic_id, username, comment FROM comments")
    all_comments = cursor.fetchall()
    comments_dict = {}
    for topic_id, username, comment in all_comments:
        if topic_id not in comments_dict:
            comments_dict[topic_id] = []
        if len(comments_dict[topic_id]) < 3:
            comments_dict[topic_id].append((username, comment))

    # Get user's liked topics if logged in
    
    if 'user_id' in session:
        cursor.execute("SELECT topic_id FROM likes WHERE user_id = ?", (session['user_id'],))
        user_liked_topic_ids = {row[0] for row in cursor.fetchall()}

    conn.close()
    return render_template('home.html', topics=topics, comments=comments_dict, user_liked_topic_ids=user_liked_topic_ids)



@app.route('/like/<int:topic_id>', methods=['POST'])
def like(topic_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = session['user_id']
    conn = sqlite3.connect("forum.db")
    c = conn.cursor()

    # Check if the user already liked the post
    c.execute("SELECT 1 FROM likes WHERE user_id = ? AND topic_id = ?", (user_id, topic_id))
    already_liked = c.fetchone()

    if already_liked:
        c.execute("DELETE FROM likes WHERE user_id = ? AND topic_id = ?", (user_id, topic_id))
    else:
        c.execute("INSERT INTO likes (user_id, topic_id) VALUES (?, ?)", (user_id, topic_id))

    # Get updated like count
    c.execute("SELECT COUNT(*) FROM likes WHERE topic_id = ?", (topic_id,))
    like_count = c.fetchone()[0]

    conn.commit()
    conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'likes': like_count, 'liked': not already_liked})

    # Fallback if JS isn't used
    return redirect(request.referrer or '/home')

@app.route('/test')
def test():
    return "Flask is working"

@app.route('/topic/<int:topic_id>')
def topic_detail(topic_id):
    if 'username' not in session:
        return redirect('/login')
    
    conn = sqlite3.connect('forum.db')
    cursor = conn.cursor()
    
    # Get the topic details
    cursor.execute('SELECT id, username, title, content FROM topics WHERE id = ?', (topic_id,))
    topic = cursor.fetchone()
    
    if not topic:
        conn.close()
        return "Topic not found", 404
    
    # Get all comments for this topic
    cursor.execute('SELECT * FROM comments WHERE topic_id = ? ORDER BY id', (topic_id,))
    comments = cursor.fetchall()
    
    # Get like count for this topic
    cursor.execute('SELECT COUNT(*) FROM likes WHERE topic_id = ?', (topic_id,))
    like_count = cursor.fetchone()[0]
    
    # Check if current user has liked this topic
    user_has_liked = False
    if 'user_id' in session:
        cursor.execute('SELECT 1 FROM likes WHERE user_id = ? AND topic_id = ?', 
                      (session['user_id'], topic_id))
        user_has_liked = cursor.fetchone() is not None
    
    conn.close()
    
    return render_template('topic_detail.html', 
                         topic_id=topic[0],
                         username=topic[1], 
                         title=topic[2], 
                         content=topic[3],
                         comments=comments,
                         like_count=like_count,
                         user_has_liked=user_has_liked)

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

    return redirect('/topic/{}'.format(topic_id))

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

    cursor.execute('''CREATE TABLE IF NOT EXISTS likes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        topic_id INTEGER NOT NULL,
                        UNIQUE(user_id, topic_id)
                        )''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)