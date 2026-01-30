"""
Social Media Platform - Main Application File
یک شبکه اجتماعی مدرن شبیه به اینستاگرام
"""
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Import models after db initialization
from models import User, Post, Story, Comment, Like, Message, ChatRoom

# Create upload directories
os.makedirs('static/uploads/posts', exist_ok=True)
os.makedirs('static/uploads/stories', exist_ok=True)
os.makedirs('static/uploads/profiles', exist_ok=True)

# ==================== Helper Functions ====================

def get_or_create_user(username):
    """Get existing user or create a new one with given username"""
    user = User.query.filter_by(username=username).first()
    if not user:
        # Generate a unique display name
        display_name = f"user_{username[:8]}"
        user = User(
            username=username,
            display_name=display_name,
            joined_date=datetime.utcnow()
        )
        db.session.add(user)
        db.session.commit()
    return user

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# ==================== Routes ====================

@app.route('/')
def index():
    """Home page - shows posts feed"""
    return render_template('index.html')

@app.route('/api/posts', methods=['GET'])
def get_posts():
    """Get all posts for feed"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    posts = Post.query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    posts_data = []
    for post in posts.items:
        post_data = {
            'id': post.id,
            'username': post.user.username,
            'display_name': post.user.display_name,
            'image_url': post.image_url,
            'caption': post.caption,
            'created_at': post.created_at.isoformat(),
            'likes_count': post.likes_count,
            'comments_count': post.comments_count,
            'is_liked': False  # This would be determined by current user
        }
        posts_data.append(post_data)
    
    return jsonify({
        'posts': posts_data,
        'has_next': posts.has_next,
        'total_pages': posts.pages
    })

@app.route('/api/posts', methods=['POST'])
def create_post():
    """Create a new post"""
    username = request.form.get('username')
    caption = request.form.get('caption', '')
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image file'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'gif', 'webp'}):
        user = get_or_create_user(username)
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join('static/uploads/posts', unique_filename)
        file.save(filepath)
        
        # Create post
        post = Post(
            user_id=user.id,
            image_url=f'/static/uploads/posts/{unique_filename}',
            caption=caption,
            likes_count=0,
            comments_count=0
        )
        db.session.add(post)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'post_id': post.id,
            'image_url': post.image_url
        })
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
def toggle_like(post_id):
    """Like or unlike a post"""
    username = request.json.get('username')
    post = Post.query.get_or_404(post_id)
    user = get_or_create_user(username)
    
    # Check if already liked
    existing_like = Like.query.filter_by(
        user_id=user.id, post_id=post.id
    ).first()
    
    if existing_like:
        # Unlike
        db.session.delete(existing_like)
        post.likes_count -= 1
        is_liked = False
    else:
        # Like
        new_like = Like(user_id=user.id, post_id=post.id)
        db.session.add(new_like)
        post.likes_count += 1
        is_liked = True
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'likes_count': post.likes_count,
        'is_liked': is_liked
    })

@app.route('/api/posts/<int:post_id>/comments', methods=['GET'])
def get_comments(post_id):
    """Get comments for a post"""
    comments = Comment.query.filter_by(post_id=post_id)\
        .order_by(Comment.created_at.asc()).all()
    
    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'username': comment.user.username,
            'display_name': comment.user.display_name,
            'text': comment.text,
            'created_at': comment.created_at.isoformat()
        })
    
    return jsonify({'comments': comments_data})

@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
def add_comment(post_id):
    """Add a comment to a post"""
    username = request.json.get('username')
    text = request.json.get('text')
    
    if not text or len(text.strip()) == 0:
        return jsonify({'error': 'Comment text is required'}), 400
    
    post = Post.query.get_or_404(post_id)
    user = get_or_create_user(username)
    
    comment = Comment(
        user_id=user.id,
        post_id=post.id,
        text=text.strip()
    )
    
    post.comments_count += 1
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'comment': {
            'id': comment.id,
            'username': user.username,
            'display_name': user.display_name,
            'text': comment.text,
            'created_at': comment.created_at.isoformat()
        }
    })

@app.route('/api/stories', methods=['GET'])
def get_stories():
    """Get active stories"""
    # Get stories from last 24 hours
    from datetime import datetime, timedelta
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    
    stories = Story.query.filter(Story.created_at >= time_threshold)\
        .order_by(Story.created_at.desc()).all()
    
    # Group by user
    stories_by_user = {}
    for story in stories:
        user_id = story.user_id
        if user_id not in stories_by_user:
            stories_by_user[user_id] = {
                'user': {
                    'username': story.user.username,
                    'display_name': story.user.display_name
                },
                'stories': []
            }
        stories_by_user[user_id]['stories'].append({
            'id': story.id,
            'media_url': story.media_url,
            'media_type': story.media_type,
            'created_at': story.created_at.isoformat()
        })
    
    return jsonify({'stories': list(stories_by_user.values())})

@app.route('/api/stories', methods=['POST'])
def create_story():
    """Create a new story"""
    username = request.form.get('username')
    
    if 'media' not in request.files:
        return jsonify({'error': 'No media file'}), 400
    
    file = request.files['media']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    user = get_or_create_user(username)
    
    # Determine media type
    filename = secure_filename(file.filename)
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if extension in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
        media_type = 'image'
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    elif extension in {'mp4', 'webm', 'mov'}:
        media_type = 'video'
        allowed_extensions = {'mp4', 'webm', 'mov'}
    else:
        return jsonify({'error': 'Invalid file type'}), 400
    
    if file and allowed_file(file.filename, allowed_extensions):
        # Generate unique filename
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join('static/uploads/stories', unique_filename)
        file.save(filepath)
        
        # Create story
        story = Story(
            user_id=user.id,
            media_url=f'/static/uploads/stories/{unique_filename}',
            media_type=media_type
        )
        db.session.add(story)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'story_id': story.id,
            'media_url': story.media_url,
            'media_type': media_type
        })
    
    return jsonify({'error': 'Invalid file'}), 400

@app.route('/api/users/search', methods=['GET'])
def search_users():
    """Search for users by username"""
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify({'users': []})
    
    users = User.query.filter(
        User.username.ilike(f'%{query}%') | 
        User.display_name.ilike(f'%{query}%')
    ).limit(10).all()
    
    users_data = [{
        'username': user.username,
        'display_name': user.display_name
    } for user in users]
    
    return jsonify({'users': users_data})

# ==================== Socket.IO Events ====================

@socketio.on('connect')
def handle_connect():
    """Handle new WebSocket connection"""
    print(f'Client connected: {request.sid}')
    emit('connected', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')

@socketio.on('join_chat')
def handle_join_chat(data):
    """Join a chat room"""
    username = data.get('username')
    target_user = data.get('target_user')
    
    if not username or not target_user:
        return
    
    # Create a unique room ID (sorted usernames to ensure same room for both users)
    room_id = '_'.join(sorted([username, target_user]))
    join_room(room_id)
    
    # Store room info
    emit('joined_chat', {
        'room_id': room_id,
        'message': f'{username} joined the chat'
    }, room=room_id)

@socketio.on('send_message')
def handle_send_message(data):
    """Send a message to a chat room"""
    username = data.get('username')
    target_user = data.get('target_user')
    message = data.get('message')
    
    if not username or not target_user or not message:
        return
    
    # Get or create users
    sender = get_or_create_user(username)
    receiver = get_or_create_user(target_user)
    
    # Create room ID
    room_id = '_'.join(sorted([username, target_user]))
    
    # Save message to database
    chat_message = Message(
        sender_id=sender.id,
        receiver_id=receiver.id,
        content=message,
        room_id=room_id
    )
    db.session.add(chat_message)
    db.session.commit()
    
    # Broadcast message to room
    emit('new_message', {
        'sender': username,
        'message': message,
        'timestamp': chat_message.timestamp.isoformat()
    }, room=room_id)

@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicator"""
    username = data.get('username')
    target_user = data.get('target_user')
    is_typing = data.get('is_typing', False)
    
    if not username or not target_user:
        return
    
    room_id = '_'.join(sorted([username, target_user]))
    emit('user_typing', {
        'username': username,
        'is_typing': is_typing
    }, room=room_id, include_self=False)

# ==================== Main Entry Point ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    print("Starting Social Media Platform Server...")
    print("Open http://localhost:5000 in your browser")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
