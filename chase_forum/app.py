from flask import Flask, render_template, request, redirect, session
import sqlite3


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed to use sessions

# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    # If the form is submitted
    if request.method == 'POST':
        username = request.form['username']  # Get username from form
        password = request.form['password']  # Get password from form
        email = request.form['email']        # Get email from form

        # Connect to the database
        conn = sqlite3.connect('Ramblr.db')
        cursor = conn.cursor()
        # Insert new user into the users table
        cursor.execute('INSERT INTO users(username, password, email) VALUES(?,?,?)', (username, password, email))
        conn.commit()  # Save changes
        conn.close()   # Close connection
        return redirect('/login')  # Redirect to login page after registration
    # If GET request, show registration form
    return render_template('register.html')

# Route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']  # Get username from form
        password = request.form['password']  # Get password from form

        # Connect to the database
        conn = sqlite3.connect('Ramblr.db')
        cursor = conn.cursor()
        # Check if user exists with given username and password
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['username'] = username  # Store username in session
            return redirect('/home')        # Redirect to home page
        else:
            return "Invalid username or password. Try again."
    # If GET request, show login form
    return render_template('login.html')

# Route for user logout
@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove username from session
    return redirect('/login')      # Redirect to login page

# Route for posting a new topic
@app.route('/post', methods=['GET', 'POST'])
def post():
    # Only allow logged-in users to post
    if 'username' not in session:
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']      # Get title from form
        content = request.form['content']  # Get content from form
        username = session['username']     # Get username from session

        # Connect to the database
        conn = sqlite3.connect('Ramblr.db')
        cursor = conn.cursor()
        # Insert new topic into topics table
        cursor.execute('INSERT INTO topics (username, title, content) VALUES (?, ?, ?)', (username, title, content))
        conn.commit()  # Save changes
        conn.close()   # Close connection

        return redirect('/home')  # Redirect to home page after posting
    # If GET request, show post form
    return render_template('post.html')

# Route for the home page (main feed)
@app.route('/home', methods=['GET', 'POST'])
def home():
    # Connect to the database
    conn = sqlite3.connect('Ramblr.db')
    cursor = conn.cursor()

    # Get all topics from the database, newest first
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

    # Get likes count for each topic
    cursor.execute("SELECT topic_id, COUNT(*) FROM likes GROUP BY topic_id")
    likes_data = cursor.fetchall()
    likes = {topic_id: count for topic_id, count in likes_data}

    # Get topics liked by current user
    user_likes = set()
    if 'username' in session:
        cursor.execute("SELECT topic_id FROM likes WHERE username = ?", (session['username'],))
        user_likes = set(row[0] for row in cursor.fetchall())

    conn.close()  # Close connection

    # Render the home page template with all data
    return render_template('home.html', topics=topics, comments=comments_dict, likes=likes, user_likes=user_likes)

# Route for viewing a single topic and its comments
@app.route('/topic/<int:topic_id>', methods=['GET'])
def view_topic(topic_id):
    conn = sqlite3.connect('Ramblr.db')
    cursor = conn.cursor()
    # Get the topic by id
    cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
    topic = cursor.fetchone()

    # Get all comments for this topic
    cursor.execute("SELECT * FROM comments WHERE topic_id = ?", (topic_id,))
    comments = cursor.fetchall()
    conn.close()

    # Render the topic detail page
    return render_template('topic_detail.html', topic=topic, comments=comments)

# Route for posting a comment on a topic
@app.route('/comment/<int:topic_id>', methods=['POST'])
def comment(topic_id):
    # Only allow logged-in users to comment
    if 'username' not in session:
        return redirect('/login')

    comment_text = request.form['comment']  # Get comment text from form
    username = session['username']          # Get username from session

    # Connect to the database
    conn = sqlite3.connect('Ramblr.db')
    cursor = conn.cursor()
    # Insert new comment into comments table
    cursor.execute('INSERT INTO comments (topic_id, username, comment) VALUES (?, ?, ?)', (topic_id, username, comment_text))
    conn.commit()  # Save changes
    conn.close()   # Close connection

    return redirect('/home')  # Redirect to home page after commenting

# Route for liking or unliking a topic
@app.route('/like/<int:topic_id>', methods=['POST'])
def like(topic_id):
    # Only allow logged-in users to like/unlike
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    conn = sqlite3.connect('Ramblr.db')
    cursor = conn.cursor()
    # Check if user already liked this topic
    cursor.execute('SELECT * FROM likes WHERE topic_id = ? AND username = ?', (topic_id, username))
    already_liked = cursor.fetchone()
    if already_liked:
        # If already liked, unlike (remove like)
        cursor.execute('DELETE FROM likes WHERE topic_id = ? AND username = ?', (topic_id, username))
    else:
        # If not liked, add like
        cursor.execute('INSERT INTO likes (topic_id, username) VALUES (?, ?)', (topic_id, username))
    conn.commit()  # Save changes
    conn.close()   # Close connection
    return redirect('/home')

# Route for deleting a topic (only by owner)
@app.route('/delete/<int:topic_id>', methods=['POST'])
def delete_topic(topic_id):
    # Only allow logged-in users to delete
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    conn = sqlite3.connect('Ramblr.db')
    cursor = conn.cursor()
    # Check if the topic belongs to the user
    cursor.execute('SELECT username FROM topics WHERE id = ?', (topic_id,))
    result = cursor.fetchone()
    if result and result[0] == username:
        # Delete topic
        cursor.execute('DELETE FROM topics WHERE id = ?', (topic_id,))
        # Delete related comments
        cursor.execute('DELETE FROM comments WHERE topic_id = ?', (topic_id,))
        # Delete related likes
        cursor.execute('DELETE FROM likes WHERE topic_id = ?', (topic_id,))
        conn.commit()  # Save changes
    conn.close()   # Close connection
    return redirect('/home')

# Route for landing page
@app.route('/')
def landingPage():
    return render_template('landingPage.html')

# Route for about us page
@app.route('/aboutus')
def aboutus():
    return render_template('about.html')

# Function to initialize the database and create tables if they don't exist

def init_db():
    conn = sqlite3.connect('Ramblr.db')
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL,
                        email TEXT NOT NULL)''')

    # Create topics table
    cursor.execute('''CREATE TABLE IF NOT EXISTS topics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT,
                        title TEXT,
                        content TEXT)''')

    # Create comments table
    cursor.execute('''CREATE TABLE IF NOT EXISTS comments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        topic_id INTEGER,
                        username TEXT,
                        comment TEXT,
                        FOREIGN KEY (topic_id) REFERENCES topics(id))''')

    # Create likes table
    cursor.execute('''CREATE TABLE IF NOT EXISTS likes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        topic_id INTEGER,
                        username TEXT,
                        FOREIGN KEY (topic_id) REFERENCES topics(id))''')
    conn.commit()  # Save changes
    conn.close()   # Close connection

# Run the app and initialize the database
if __name__ == '__main__':
    init_db()  # Create tables if not exist
    app.run(debug=True, host = '0.0.0.0', port = '5000')


