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
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


# Import models after db initialization
from models import User, Post, Story, Comment, Like, Message, ChatRoom

# Create upload directories
os.makedirs('static/uploads/posts', exist_ok=True)
os.makedirs('static/uploads/stories', exist_ok=True)
os.makedirs('static/uploads/profiles', exist_ok=True)

# ==================== Helper Functions ====================

def get_or_create_user(username):
    """Get existing user or create a new one with given username"""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            # Generate a unique display name
            display_name = f"کاربر {username}"
            user = User(
                username=username,
                display_name=display_name,
                joined_date=datetime.utcnow()
            )
            db.session.add(user)
            db.session.commit()
            print(f"✅ کاربر جدید ایجاد شد: {username}")
        return user
    except Exception as e:
        print(f"❌ خطا در ایجاد کاربر {username}: {str(e)}")
        # در صورت خطا، یک کاربر موقت ایجاد کنیم
        user = User(
            username=username,
            display_name=f"کاربر {username}",
            joined_date=datetime.utcnow()
        )
        db.session.add(user)
        try:
            db.session.commit()
        except:
            db.session.rollback()
        return user

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# ==================== Routes (Updated) ====================

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
            'is_liked': False
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
    try:
        # Debug: Print form data
        print(f"Form data: {request.form}")
        print(f"Files: {request.files}")
        
        username = request.form.get('username')
        caption = request.form.get('caption', '')
        
        print(f"Username: {username}, Caption: {caption}")
        
        if 'image' not in request.files:
            print("No image file in request")
            return jsonify({'error': 'No image file', 'success': False}), 400
        
        file = request.files['image']
        print(f"File: {file}, Filename: {file.filename}")
        
        if file.filename == '':
            print("Empty filename")
            return jsonify({'error': 'No selected file', 'success': False}), 400
        
        # Check file extension
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        filename = file.filename
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        print(f"File extension: {file_ext}")
        
        if file_ext not in allowed_extensions:
            print(f"Invalid file extension: {file_ext}")
            return jsonify({'error': f'Invalid file type. Allowed: {allowed_extensions}', 'success': False}), 400
        
        # Get or create user
        user = get_or_create_user(username)
        print(f"User: {user.username}, ID: {user.id}")
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        upload_path = os.path.join(app.root_path, 'static', 'uploads', 'posts')
        
        # Ensure directory exists
        os.makedirs(upload_path, exist_ok=True)
        
        filepath = os.path.join(upload_path, unique_filename)
        print(f"Saving file to: {filepath}")
        
        # Save file
        file.save(filepath)
        
        # Create post
        post = Post(
            user_id=user.id,
            image_url=f'/static/uploads/posts/{unique_filename}',
            caption=caption,
            likes_count=0,
            comments_count=0,
            created_at=datetime.utcnow()
        )
        
        db.session.add(post)
        db.session.commit()
        
        print(f"Post created successfully. ID: {post.id}")
        
        return jsonify({
            'success': True,
            'post_id': post.id,
            'image_url': post.image_url,
            'message': 'پست با موفقیت ایجاد شد'
        })
    
    except Exception as e:
        print(f"Error creating post: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/stories', methods=['POST'])
def create_story():
    """Create a new story"""
    try:
        print(f"Story form data: {request.form}")
        print(f"Story files: {request.files}")
        
        username = request.form.get('username')
        
        if 'media' not in request.files:
            print("No media file in request")
            return jsonify({'error': 'No media file', 'success': False}), 400
        
        file = request.files['media']
        
        if file.filename == '':
            print("Empty filename for story")
            return jsonify({'error': 'No selected file', 'success': False}), 400
        
        # Get or create user
        user = get_or_create_user(username)
        
        # Determine media type
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
            media_type = 'image'
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            upload_dir = 'static/uploads/stories'
        elif file_ext in {'mp4', 'webm', 'mov', 'avi'}:
            media_type = 'video'
            allowed_extensions = {'mp4', 'webm', 'mov', 'avi'}
            upload_dir = 'static/uploads/stories'
        else:
            return jsonify({'error': 'Invalid file type', 'success': False}), 400
        
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Invalid file type. Allowed: {allowed_extensions}', 'success': False}), 400
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        upload_path = os.path.join(app.root_path, upload_dir)
        
        # Ensure directory exists
        os.makedirs(upload_path, exist_ok=True)
        
        filepath = os.path.join(upload_path, unique_filename)
        file.save(filepath)
        
        # Create story
        story = Story(
            user_id=user.id,
            media_url=f'/static/uploads/stories/{unique_filename}',
            media_type=media_type,
            created_at=datetime.utcnow()
        )
        
        db.session.add(story)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'story_id': story.id,
            'media_url': story.media_url,
            'media_type': media_type,
            'message': 'استوری با موفقیت ایجاد شد'
        })
    
    except Exception as e:
        print(f"Error creating story: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/chats/users', methods=['GET'])
def get_chat_users():
    """Get list of users for chat"""
    try:
        username = request.args.get('username', '')
        
        # Get all users except current user
        if username:
            users = User.query.filter(User.username != username)\
                .order_by(User.username)\
                .limit(20)\
                .all()
        else:
            users = User.query.order_by(User.username).limit(20).all()
        
        users_data = [{
            'username': user.username,
            'display_name': user.display_name,
            'last_active': user.joined_date.isoformat()
        } for user in users]
        
        return jsonify({
            'success': True,
            'users': users_data
        })
    
    except Exception as e:
        print(f"Error getting chat users: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/chats/messages', methods=['GET'])
def get_chat_messages():
    """Get chat messages between two users"""
    try:
        user1 = request.args.get('user1')
        user2 = request.args.get('user2')
        
        if not user1 or not user2:
            return jsonify({'error': 'Both users required', 'success': False}), 400
        
        # Get users
        user1_obj = User.query.filter_by(username=user1).first()
        user2_obj = User.query.filter_by(username=user2).first()
        
        if not user1_obj or not user2_obj:
            return jsonify({'error': 'User not found', 'success': False}), 404
        
        # Create room ID
        room_id = '_'.join(sorted([user1, user2]))
        
        # Get messages
        messages = Message.query.filter_by(room_id=room_id)\
            .order_by(Message.timestamp.asc())\
            .all()
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'sender': msg.sender.username,
                'receiver': msg.receiver.username,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'is_read': msg.is_read
            })
        
        return jsonify({
            'success': True,
            'messages': messages_data,
            'room_id': room_id
        })
    
    except Exception as e:
        print(f"Error getting chat messages: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/chats/messages', methods=['POST'])
def save_chat_message():
    """Save a chat message"""
    try:
        data = request.json
        sender_username = data.get('sender')
        receiver_username = data.get('receiver')
        content = data.get('content')
        
        if not all([sender_username, receiver_username, content]):
            return jsonify({'error': 'Missing required fields', 'success': False}), 400
        
        # Get users
        sender = User.query.filter_by(username=sender_username).first()
        receiver = User.query.filter_by(username=receiver_username).first()
        
        if not sender or not receiver:
            return jsonify({'error': 'User not found', 'success': False}), 404
        
        # Create room ID
        room_id = '_'.join(sorted([sender_username, receiver_username]))
        
        # Save message
        message = Message(
            sender_id=sender.id,
            receiver_id=receiver.id,
            content=content,
            room_id=room_id,
            timestamp=datetime.utcnow()
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': {
                'id': message.id,
                'sender': sender_username,
                'receiver': receiver_username,
                'content': content,
                'timestamp': message.timestamp.isoformat()
            }
        })
    
    except Exception as e:
        print(f"Error saving chat message: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e), 'success': False}), 500
