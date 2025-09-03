from flask import Flask, render_template, request, redirect, session, jsonify
import psycopg2
from dotenv import load_dotenv
import psycopg2.extras
from werkzeug.utils import secure_filename
import bcrypt
import os
import os
from flask import url_for
from urllib.parse import urlparse

load_dotenv()
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'img', 'profile_pics')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.secret_key = os.getenv("SECRET_KEY")
DATABASE_URL = os.getenv("DB_URL")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        byte_password = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(byte_password, salt)
        email = request.form['email']

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
    if 'username' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Get the current user's profile picture URL for the nav bar
            cursor.execute('''
                SELECT username, profile_pic 
                FROM users 
                WHERE id = %s
            ''', (session['user_id'],))
            current_user_data = cursor.fetchone()
            
            # Get all topics with like and comment counts and author's profile pic
            cursor.execute('''
                SELECT t.id, t.title, t.content, t.username, t.created_at,
                       u.profile_pic as author_profile_pic,
                       (SELECT COUNT(*) FROM likes WHERE topic_id = t.id) as like_count,
                       (SELECT COUNT(*) FROM comments WHERE topic_id = t.id) as comment_count
                FROM topics t
                JOIN users u ON t.username = u.username
                ORDER BY t.created_at DESC
            ''')
            topics_data = cursor.fetchall()
            
            # Process topics to add truncated_content and profile pic URL
            processed_topics = []
            for topic in topics_data:
                topic_dict = dict(topic)
                topic_dict['truncated_content'] = (topic['content'][:250] + '...') if len(topic['content']) > 250 else topic['content']
                
                # Set the author's profile picture URL
                if topic['author_profile_pic']:
                    topic_dict['author_profile_pic_url'] = url_for('static', filename=topic['author_profile_pic'])
                else:
                    # Check if default profile picture exists for the author
                    profile_pic_folder = os.path.join(app.static_folder, "img", "profile_pics")
                    default_pic_path = os.path.join(profile_pic_folder, f"{topic['username']}.png")
                    if os.path.exists(default_pic_path):
                        topic_dict['author_profile_pic_url'] = url_for('static', filename=f"img/profile_pics/{topic['username']}.png")
                    else:
                        topic_dict['author_profile_pic_url'] = url_for('static', filename="img/profile_pics/default.jpg")
                
                processed_topics.append(topic_dict)
            
            # Get like status for each topic
            liked_topics = set()
            cursor.execute('''
                SELECT topic_id FROM likes 
                WHERE user_id = %s
            ''', (session['user_id'],))
            for row in cursor.fetchall():
                liked_topics.add(row['topic_id'])
            
            # Get comments for each topic
            cursor.execute('''
                SELECT c.topic_id, u.username, c.content 
                FROM comments c
                JOIN users u ON c.user_id = u.id
                ORDER BY c.created_at DESC
            ''')
            
            comments_dict = {}
            for topic_id, username, content in cursor.fetchall():
                if topic_id not in comments_dict:
                    comments_dict[topic_id] = []
                if len(comments_dict[topic_id]) < 3:  # Only keep the 3 most recent comments
                    comments_dict[topic_id].append((username, content))
        
        # Determine current user's profile picture URL for the nav bar
        current_user_profile_pic = None
        if current_user_data['profile_pic']:
            current_user_profile_pic = url_for('static', filename=current_user_data['profile_pic'])
        else:
            profile_pic_folder = os.path.join(app.static_folder, "img", "profile_pics")
            user_pic_filename = f"{current_user_data['username']}.png"
            user_pic_path = os.path.join(profile_pic_folder, user_pic_filename)
            
            if os.path.exists(user_pic_path):
                current_user_profile_pic = url_for('static', filename=f"img/profile_pics/{current_user_data['username']}.png")
            else:
                current_user_profile_pic = url_for('static', filename="img/profile_pics/default.jpg")
        
        return render_template('home.html', 
                             topics=processed_topics,
                             comments=comments_dict,
                             liked_topics=liked_topics,
                             current_user_profile_pic=current_user_profile_pic,
                             username=session['username'])
                             
    except Exception as e:
        conn.rollback()
        return f"An error occurred: {e}"
    finally:
        conn.close()

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
                SELECT c.topic_id, c.content, TO_CHAR(c.created_at, 'YYYY-MM-DD HH24:MI') as created_at, 
                       t.title as topic_title, u.username as user_username
                FROM comments c
                JOIN topics t ON c.topic_id = t.id
                JOIN users u ON c.user_id = u.id
                WHERE u.username = %s
                ORDER BY c.created_at DESC
                LIMIT 5
            ''', (username,))
            comments = [dict(zip(['topic_id', 'content', 'created_at', 'topic_title', 'user_username'], row)) for row in cursor.fetchall()]
        
        profile_pic_url = url_for("static", filename=f"img/profile_pics/{username}.png")
        profile_pic_folder = os.path.join(app.static_folder, "img", "profile_pics")
        user_pic_filename = f"{username}.png"
        user_pic_path = os.path.join(profile_pic_folder, user_pic_filename)

        if os.path.exists(user_pic_path):
            profile_pic_url = url_for("static", filename=f"img/profile_pics/{username}.png")
        else:
            profile_pic_url = url_for("static", filename="img/profile_pics/default.jpg")
        
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
                             },
                             profile_pic_url=profile_pic_url)
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

@app.route('/')
def landingPage():
    return render_template('landingPage.html')

@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    if 'profile_pic' not in request.files:
        return redirect(request.referrer or url_for('profile'))

    file = request.files['profile_pic']
    if file.filename == '':
        return redirect(request.referrer or url_for('profile'))

    if file and allowed_file(file.filename):
        user_id = session.get('user_id')
        if not user_id:
            return redirect('/login')

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
                username = cur.fetchone()[0]

                # Get the file extension
                ext = file.filename.rsplit('.', 1)[1].lower()
                safe_username = secure_filename(username)
                filename = f"{safe_username}.{ext}"

                # Save the file
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])
                    
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                # Update the database with the new filename
                relative_path = f"img/profile_pics/{filename}"
                cur.execute(
                    "UPDATE users SET profile_pic = %s WHERE id = %s",
                    (relative_path, user_id)
                )
                conn.commit()
                
            return redirect(url_for('profile', username=username))
            
        except Exception as e:
            conn.rollback()
            return f"An error occurred: {e}"
        finally:
            conn.close()
            
    return 'File type not allowed', 400

@app.route('/edit/<int:topic_id>', methods=['GET', 'POST'])
def edit_topic(topic_id):
    if 'username' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute('SELECT * FROM topics WHERE id = %s AND username = %s', 
                         (topic_id, session['username']))
            topic = cursor.fetchone()
            
            if not topic:
                return "Topic not found or unauthorized", 404
            
            if request.method == 'POST':
                title = request.form['title']
                content = request.form['content']
                
                cursor.execute(
                    'UPDATE topics SET title = %s, content = %s WHERE id = %s',
                    (title, content, topic_id)
                )
                conn.commit()
                return redirect('/home')
            
            return render_template('edit_topic.html', topic=topic)
    except Exception as e:
        conn.rollback()
        return f"An error occurred: {e}"
    finally:
        conn.close()

@app.route('/delete/<int:topic_id>', methods=['POST'])
def delete_topic(topic_id):
    if 'username' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM topics WHERE id = %s AND username = %s', 
                         (topic_id, session['username']))
            if cursor.rowcount == 0:
                return "Topic not found or unauthorized", 404
            conn.commit()
            return redirect('/home')
    except Exception as e:
        conn.rollback()
        return f"An error occurred: {e}"
    finally:
        conn.close()

def init_db():
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

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)