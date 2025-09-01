from flask import Flask, render_template, request, redirect, session, jsonify
<<<<<<< HEAD
import sqlite3
from werkzeug.utils import secure_filename
=======
import psycopg2
import psycopg2.extras
>>>>>>> 3385d1a4a10b35e119367763568324124482c41b
import bcrypt
import os
from urllib.parse import urlparse





ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.secret_key = 'your_secret_key'

<<<<<<< HEAD
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'img', 'profile_pics')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 MB
DEFAULT_AVATAR = "img/profile_pics/default.jpg"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/profile")
def profile():
    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("forum.db")
    cursor = conn.cursor()

    # Get user info
    cursor.execute("SELECT * FROM users WHERE username = ?", (session['username'],))
    user = cursor.fetchone()
    if user is None:
        conn.close()
        return redirect('/login')
    raw_pic = user[4]  # profile_pic column
    display_pic = raw_pic if raw_pic else "img/profile_pics/default.jpg"
    user_dict = {
        "username": user[1],   # username column
        "profile_pic": display_pic # profile_pic column
    }

    # Get user posts
    cursor.execute('''
        SELECT topics.id, topics.username, topics.title, topics.content,
               COUNT(likes.id) AS like_count,
               users.profile_pic
        FROM topics
        LEFT JOIN likes ON topics.id = likes.topic_id
        LEFT JOIN users ON topics.username = users.username
        WHERE topics.username = ?
        GROUP BY topics.id
        ORDER BY topics.id DESC
    ''', (session['username'],))
    
    topics_raw = cursor.fetchall()
    topics = []

    for topic_id, username, title, content, like_count, profile_pic in topics_raw:
        truncated_content = content[:250] + '...' if len(content) > 40 else content
        #fallback to default if empty
        profile_pic = profile_pic if profile_pic else "img/profile_pics/default.jpg"
    
        
        topics.append({
            'id': topic_id,
            'username': username,
            'title': title,
            'truncated_content': truncated_content,
            'full_content': content,
            'likes': like_count,
            'profile_pic': profile_pic
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

    # Get user's liked topics
    user_liked_topic_ids = set()
    if 'user_id' in session:
        cursor.execute("SELECT topic_id FROM likes WHERE user_id = ?", (session['user_id'],))
        user_liked_topic_ids = {row[0] for row in cursor.fetchall()}

    conn.close()

    # Render profile with posts + comments
    return render_template(
        "profile.html",
        user=user_dict,
        topics=topics,
        comments=comments_dict,
        user_liked_topic_ids=user_liked_topic_ids
    )

#Uploading user profile picture
@app.route('/upload_profile_pic', methods=['GET', 'POST'])
def upload_profile_pic():
    try:
        if 'username' not in session:
            print("User not logged in.")
            return redirect('/login')

        print("Form Keys:", request.form.keys())
        print("File Keys:", request.files.keys())

        if 'profile_pic' not in request.files:
            print("No file part in request")
            return "No file part in request", 400

        file = request.files['profile_pic']
        
        print("Filename:", file.filename)

        if file.filename == '':
            print("Empty filename")
            return "No file selected", 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_folder = app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            relative_path = os.path.join('img', 'profile_pics', filename).replace("\\", "/")

            conn = sqlite3.connect('forum.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET profile_pic = ? WHERE username = ?', (relative_path, session['username']))
            conn.commit()
            conn.close()

            print("Upload successful. Redirecting to profile.")
            return redirect('/profile', file_name=file.fiilename)
        else:
            print("File type not allowed")
            return "File type not allowed", 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Server error: {str(e)}", 500
=======
DATABASE_URL = "postgresql://postgres:sinenn@localhost:5432/Ramblr"

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn
>>>>>>> 3385d1a4a10b35e119367763568324124482c41b

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        byte_password = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(byte_password, salt)
        email = request.form['email']

<<<<<<< HEAD
        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users(username, password, email, profile_pic) VALUES(?,?,?,?)', (username, hashed_password, email, DEFAULT_AVATAR))
        conn.commit()
        conn.close()
        return redirect('/login')
=======
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO users(username, password, email) VALUES(%s, %s, %s) RETURNING id',
                    (username, hashed_password, email)
                )
                conn.commit()
            return redirect('/login')
        except Exception as e:
            conn.rollback()
            return f"An error occurred: {e}"
        finally:
            conn.close()
>>>>>>> 3385d1a4a10b35e119367763568324124482c41b
    return render_template('register.html')

@app.route('/users')
def list_users():
    if "user_id" not in session: 
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT is_admin FROM users WHERE id = %s", (session["user_id"],))
    user = cur.fetchone()

    if not user or not user["is_admin"]:
        return "Access denied", 403

    cur.execute("SELECT id, username, email, is_admin FROM users")
    users = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("users.html", users=users)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        byte_password = password.encode('utf-8')

        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute('SELECT id, password FROM users WHERE username = %s', (username,))
                user = cursor.fetchone()
                
                if user and bcrypt.checkpw(byte_password, user['password'].tobytes()):
                    session['username'] = username
                    session['user_id'] = user['id']
                    return redirect('/home')
                else:
                    return render_template('error_boundary.html')
        finally:
            conn.close()
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

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('INSERT INTO topics (username, title, content) VALUES (%s, %s, %s)', (username, title, content))
                conn.commit()
            return redirect('/home')
        except Exception as e:
            conn.rollback()
            return f"An error occurred: {e}"
        finally:
            conn.close()
    return render_template('post.html')

@app.route('/home', methods=['GET'])
def home():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
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
                truncated_content = content[:250] + '...' if len(content) > 40 else content
                liked_by_user = topic_id in user_liked_topic_ids

<<<<<<< HEAD
    # Get topics with like counts
    cursor.execute('''
        SELECT topics.id, topics.username, topics.title, topics.content,
               COUNT(likes.id) AS like_count,
               users.profile_pic
        FROM topics
        LEFT JOIN likes ON topics.id = likes.topic_id
        LEFT JOIN users ON topics.username = users.username
        GROUP BY topics.id
        ORDER BY topics.id DESC
    ''')
    topics_raw = cursor.fetchall()
    user_liked_topic_ids = set()
    topics = []
    
    
    for topic in topics_raw:
        topic_id, username, title, content, like_count, profile_pic = topic
        truncated_content = content[:250] + '...' if len(content) > 40 else content
        liked_by_user = topic_id in user_liked_topic_ids
        profile_pic = profile_pic if profile_pic else "img/profile_pics/default.jpg"
        topics.append({
            'id': topic_id,
            'username': username,
            'title': title,
            'truncated_content': truncated_content,
            'full_content': content,
            'likes': like_count,
            'liked_by_user': liked_by_user,
            'profile_pic': profile_pic
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
    username = session['username']
    conn.close()
    return render_template('home.html', topics=topics, comments=comments_dict, user_liked_topic_ids=user_liked_topic_ids, username=username)


@app.route('/myposts', methods=['GET'])
def getuserposts():
    conn = sqlite3.connect('forum.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT topics.id, topics.username, topics.title, topics.content,
            COUNT(likes.id) AS like_count
        FROM topics
        LEFT JOIN likes ON topics.id = likes.topic_id
        WHERE topics.username = ?
        GROUP BY topics.id
        ORDER BY topics.id DESC
    ''', (session['username'],))

    topics_raw = cursor.fetchall()
    user_liked_topic_ids = set()
    topics = []
    
    for topic in topics_raw:
        topic_id, username, title, content, like_count = topic
        truncated_content = content[:250] + '...' if len(content) > 40 else content
        liked_by_user = topic_id in user_liked_topic_ids
=======
                topics.append({
                    'id': topic_id,
                    'username': username,
                    'title': title,
                    'truncated_content': truncated_content,
                    'full_content': content,
                    'likes': like_count,
                    'liked_by_user': liked_by_user
                })
>>>>>>> 3385d1a4a10b35e119367763568324124482c41b

           
            cursor.execute("""
            SELECT c.topic_id, u.username, c.content 
            FROM comments c
            JOIN users u ON c.user_id = u.id
        """)

            all_comments = cursor.fetchall()
            comments_dict = {}
            for topic_id, username, content in all_comments:
                if topic_id not in comments_dict:
                    comments_dict[topic_id] = []
                if len(comments_dict[topic_id]) < 3:
                    comments_dict[topic_id].append((username, content))

<<<<<<< HEAD
    # Get user's liked topics if logged in
    
    if 'user_id' in session:
        cursor.execute("SELECT topic_id FROM likes WHERE user_id = ?", (session['user_id'],))
        user_liked_topic_ids = {row[0] for row in cursor.fetchall()}

    conn.close()
    return render_template('userposts.html', topics=topics, comments=comments_dict, user_liked_topic_ids=user_liked_topic_ids)
=======
                      
            if 'user_id' in session:
                cursor.execute("SELECT topic_id FROM likes WHERE user_id = %s", (session['user_id'],))
                user_liked_topic_ids = {row[0] for row in cursor.fetchall()}

        conn.close()
        return render_template('home.html', topics=topics, comments=comments_dict, user_liked_topic_ids=user_liked_topic_ids)
    except Exception as e:
        conn.rollback()
        return f"An error occurred: {e}"
    finally:
        conn.close()
>>>>>>> 3385d1a4a10b35e119367763568324124482c41b

        

@app.route('/like/<int:topic_id>', methods=['POST'])
def like(topic_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = session['user_id']
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Check if the user already liked the post
            cursor.execute("SELECT 1 FROM likes WHERE user_id = %s AND topic_id = %s", (user_id, topic_id))
            already_liked = cursor.fetchone()

            if already_liked:
                cursor.execute("DELETE FROM likes WHERE user_id = %s AND topic_id = %s", (user_id, topic_id))
            else:
                cursor.execute("INSERT INTO likes (user_id, topic_id) VALUES (%s, %s)", (user_id, topic_id))

            cursor.execute("SELECT COUNT(*) FROM likes WHERE topic_id = %s", (topic_id,))
            like_count = cursor.fetchone()[0]

            conn.commit()
        conn.close()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'likes': like_count, 'liked': not already_liked})

        return redirect(request.referrer or '/home')
    except Exception as e:
        conn.rollback()
        return f"An error occurred: {e}"
    finally:
        conn.close()

@app.route('/test')
def test():
    return "Flask is working"

@app.route('/profile')
@app.route('/profile/<username>')
def profile(username=None):
    if 'username' not in session:
        return redirect('/login')
        
    # If no username is provided, use the current user's username
    if username is None:
        username = session['username']
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            
            cursor.execute('SELECT id, username, email FROM users WHERE username = %s', (username,))
            user_profile = cursor.fetchone()
            
            if not user_profile:
                conn.close()
                return "User not found", 404
            
            cursor.execute('SELECT COUNT(*) FROM topics WHERE username = %s', (username,))
            topic_count = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) 
                FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE u.username = %s
            ''', (username,))
            comment_count = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) 
                FROM likes 
                JOIN topics ON likes.topic_id = topics.id 
                WHERE topics.username = %s
            ''', (username,))
            likes_received = cursor.fetchone()[0]
            
            # Get recent user activity
            cursor.execute('''
                SELECT id, title, 
                       TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') as created_at,
                       (SELECT COUNT(*) FROM comments WHERE topic_id = topics.id) as comment_count,
                       (SELECT COUNT(*) FROM likes WHERE topic_id = topics.id) as likes
                FROM topics 
                WHERE username = %s
                ORDER BY created_at DESC
                LIMIT 5
            ''', (username,))
            topics = [dict(zip(['id', 'title', 'created_at', 'comment_count', 'likes'], row)) for row in cursor.fetchall()]
            
            cursor.execute('''
                SELECT c.topic_id, c.content, TO_CHAR(c.created_at, 'YYYY-MM-DD HH24:MI') as created_at, t.title as topic_title, u.username as user_username
                FROM comments c
                JOIN topics t ON c.topic_id = t.id
                JOIN users u ON c.user_id = u.id
                WHERE u.username = %s
                ORDER BY c.created_at DESC
                LIMIT 5
            ''', (username,))
            comments = [dict(zip(['topic_id', 'content', 'created_at', 'topic_title', 'user_username'], row)) for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template('profile.html',
                             user_profile=dict(zip(['id', 'username', 'email'], user_profile)),
                             user_stats={
                                 'topic_count': topic_count,
                                 'comment_count': comment_count,
                                 'likes_received': likes_received
                             },
                             user_activity={
                                 'topics': topics,
                                 'comments': comments
                             })
    except Exception as e:
        conn.rollback()
        return f"An error occurred: {e}"
    finally:
        conn.close()

@app.route('/topic/<int:topic_id>')
def topic_detail(topic_id):
    if 'username' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Get the topic details
            cursor.execute('SELECT id, username, title, content FROM topics WHERE id = %s', (topic_id,))
            topic = cursor.fetchone()
            
            if not topic:
                conn.close()
                return "Topic not found", 404
            
            # Get all comments for this topic
            cursor.execute('SELECT * FROM comments WHERE topic_id = %s ORDER BY id', (topic_id,))
            comments = cursor.fetchall()
            
            # Get like count for this topic
            cursor.execute('SELECT COUNT(*) FROM likes WHERE topic_id = %s', (topic_id,))
            like_count = cursor.fetchone()[0]
            
            # Check if current user has liked this topic
            user_has_liked = False
            if 'user_id' in session:
                cursor.execute('SELECT 1 FROM likes WHERE user_id = %s AND topic_id = %s', 
                              (session['user_id'], topic_id))
                user_has_liked = cursor.fetchone() is not None
        
        conn.close()
        
        return render_template('topic_detail.html', 
                             topic_id=topic['id'],
                             username=topic['username'], 
                             title=topic['title'], 
                             content=topic['content'],
                             comments=comments,
                             like_count=like_count,
                             user_has_liked=user_has_liked)
    except Exception as e:
        conn.rollback()
        return f"An error occurred: {e}"
    finally:
        conn.close()

@app.route('/comment/<int:topic_id>', methods=['POST'])
def comment(topic_id):
    if 'user_id' not in session:
        return redirect('/login')

    comment_text = request.form['comment']
    user_id = session['user_id']

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('INSERT INTO comments (topic_id, user_id, content) VALUES (%s, %s, %s)', 
                         (topic_id, user_id, comment_text))
            conn.commit()
        return redirect(f'/topic/{topic_id}')
    except Exception as e:
        conn.rollback()
        return f"An error occurred: {e}"
    finally:
        conn.close()

@app.route('/delete/<int:topic_id>', methods=['POST'])
def delete_post(topic_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    username = session['username']
    conn = sqlite3.connect('forum.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM topics WHERE id = ?', (topic_id,))
    topic = cursor.fetchone()
    
    if not topic:
        conn.close()
        return jsonify({'error': 'Post not found'}), 404
    
    if topic[0] != username:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403
    cursor.execute('DELETE FROM comments WHERE topic_id = ?', (topic_id,))
    cursor.execute('DELETE FROM likes WHERE topic_id = ?', (topic_id,))
    cursor.execute('DELETE FROM topics WHERE id = ?', (topic_id,))
    
    conn.commit()
    conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    return redirect('/myposts')

@app.route('/edit/<int:topic_id>', methods=['GET', 'POST'])
def edit_post(topic_id):
    if 'username' not in session:
        return redirect('/login')

    username = session['username']
    conn = sqlite3.connect('forum.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username, title, content FROM topics WHERE id = ?', (topic_id,))
    topic = cursor.fetchone()
    
    if not topic:
        conn.close()
        return "Post not found", 404
    
    if topic[0] != username:
        conn.close()
        return "Unauthorized", 403

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        cursor.execute('UPDATE topics SET title = ?, content = ? WHERE id = ?', 
                      (title, content, topic_id))
        conn.commit()
        conn.close()
        
        return redirect('/home')

    conn.close()
    return render_template('edit_post.html', 
                         topic_id=topic_id,
                         title=topic[1], 
                         content=topic[2])



@app.route('/')
def landingPage():
    return render_template('landingPage.html')

def init_db():
<<<<<<< HEAD
    conn = sqlite3.connect('forum.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL,
                        email TEXT NOT NULL,
                        profile_pic TEXT)
                        ''')
        

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
=======
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
           
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password BYTEA NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create topics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS topics (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
                )
            ''')
            
            # Create likes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS likes (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    topic_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
                    UNIQUE(user_id, topic_id)
                )
            ''')
            
            # Create comments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS comments (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    topic_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
    finally:
        conn.close()
>>>>>>> 3385d1a4a10b35e119367763568324124482c41b

if __name__ == '__main__':
    init_db()
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)