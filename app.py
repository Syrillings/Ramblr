from flask import Flask, render_template, request, redirect, session, jsonify
import psycopg2
import bcrypt
from dotenv import load_dotenv
import os
import base64

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT')
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT username FROM users WHERE username = %s', (username,))
        if cursor.fetchone():
            conn.close()
            return "Username already exists."
        
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        hashed_b64 = base64.b64encode(hashed).decode('utf-8')
        
        cursor.execute('INSERT INTO users(username, password, email) VALUES(%s,%s,%s)', 
                      (username, hashed_b64, email))
        conn.commit()
        conn.close()
        
        return redirect('/login')
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, password FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            stored_hash = base64.b64decode(user[1])
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                session['username'] = username
                session['user_id'] = user[0]
                return redirect('/home')
        
        return "Invalid credentials."
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect('/login')
        
    conn = get_db_connection()
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
    
    topics = []
    for topic in topics_raw:
        topic_id, username, title, content, like_count = topic
        truncated_content = content[:100] + '...' if len(content) > 100 else content
        topics.append({
            'id': topic_id,
            'username': username,
            'title': title,
            'truncated_content': truncated_content,
            'likes': like_count
        })
    
    # Get user's liked topics
    user_liked_topic_ids = set()
    if 'user_id' in session:
        cursor.execute("SELECT topic_id FROM likes WHERE user_id = %s", (session['user_id'],))
        user_liked_topic_ids = {row[0] for row in cursor.fetchall()}
    
    # Get comments
    cursor.execute("SELECT topic_id, username, comment FROM comments")
    all_comments = cursor.fetchall()
    comments_dict = {}
    for topic_id, username, comment in all_comments:
        if topic_id not in comments_dict:
            comments_dict[topic_id] = []
        if len(comments_dict[topic_id]) < 3:
            comments_dict[topic_id].append((username, comment))
    
    conn.close()
    return render_template('home.html', topics=topics, comments=comments_dict, user_liked_topic_ids=user_liked_topic_ids)

@app.route('/post', methods=['GET', 'POST'])
def post():
    if 'username' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        username = session['username']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO topics (username, title, content) VALUES (%s, %s, %s)', 
                      (username, title, content))
        conn.commit()
        conn.close()
        
        return redirect('/home')
        
    return render_template('post.html')

@app.route('/like/<int:topic_id>', methods=['POST'])
def like(topic_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if already liked
    cursor.execute("SELECT 1 FROM likes WHERE user_id = %s AND topic_id = %s", (user_id, topic_id))
    already_liked = cursor.fetchone()
    
    if already_liked:
        cursor.execute("DELETE FROM likes WHERE user_id = %s AND topic_id = %s", (user_id, topic_id))
        liked = False
    else:
        cursor.execute("INSERT INTO likes (user_id, topic_id) VALUES (%s, %s)", (user_id, topic_id))
        liked = True
    
    # Get updated count
    cursor.execute("SELECT COUNT(*) FROM likes WHERE topic_id = %s", (topic_id,))
    like_count = cursor.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'likes': like_count, 'liked': liked})
    
    return redirect('/home')

@app.route('/topic/<int:topic_id>')
def topic_detail(topic_id):
    if 'username' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, username, title, content FROM topics WHERE id = %s', (topic_id,))
    topic = cursor.fetchone()
    
    if not topic:
        conn.close()
        return "Topic not found", 404
    
    cursor.execute('SELECT * FROM comments WHERE topic_id = %s ORDER BY id', (topic_id,))
    comments = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM likes WHERE topic_id = %s', (topic_id,))
    like_count = cursor.fetchone()[0]
    
    user_has_liked = False
    if 'user_id' in session:
        cursor.execute('SELECT 1 FROM likes WHERE user_id = %s AND topic_id = %s', 
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO comments (topic_id, username, comment) VALUES (%s, %s, %s)', 
                  (topic_id, username, comment_text))
    conn.commit()
    conn.close()
    
    return redirect(f'/topic/{topic_id}')

@app.route('/')
def landingPage():
    return render_template('landingPage.html')

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        email TEXT NOT NULL)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS topics (
                        id SERIAL PRIMARY KEY,
                        username TEXT NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS comments (
                        id SERIAL PRIMARY KEY,
                        topic_id INTEGER,
                        username TEXT,
                        comment TEXT,
                        FOREIGN KEY (topic_id) REFERENCES topics(id))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS likes (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        topic_id INTEGER NOT NULL,
                        UNIQUE(user_id, topic_id))''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)