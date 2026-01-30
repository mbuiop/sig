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

# ==================== Fix Like and Comment Issues ====================

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
def toggle_like(post_id):
    """Like or unlike a post"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'success': False}), 400
            
        username = data.get('username')
        if not username:
            return jsonify({'error': 'Username is required', 'success': False}), 400
        
        print(f"Toggle like - Post: {post_id}, User: {username}")
        
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found', 'success': False}), 404
        
        user = get_or_create_user(username)
        
        # Check if already liked
        existing_like = Like.query.filter_by(
            user_id=user.id, post_id=post.id
        ).first()
        
        if existing_like:
            # Unlike
            db.session.delete(existing_like)
            post.likes_count = max(0, post.likes_count - 1)
            is_liked = False
            print(f"User {username} unliked post {post_id}")
        else:
            # Like
            new_like = Like(user_id=user.id, post_id=post.id)
            db.session.add(new_like)
            post.likes_count += 1
            is_liked = True
            print(f"User {username} liked post {post_id}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'likes_count': post.likes_count,
            'is_liked': is_liked
        })
    
    except Exception as e:
        print(f"Error in toggle_like: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/posts/<int:post_id>/comments', methods=['GET'])
def get_comments(post_id):
    """Get comments for a post"""
    try:
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
        
        return jsonify({
            'success': True,
            'comments': comments_data,
            'count': len(comments_data)
        })
    
    except Exception as e:
        print(f"Error in get_comments: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
def add_comment(post_id):
    """Add a comment to a post"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'success': False}), 400
            
        username = data.get('username')
        text = data.get('text')
        
        if not username:
            return jsonify({'error': 'Username is required', 'success': False}), 400
        
        if not text or len(text.strip()) == 0:
            return jsonify({'error': 'Comment text is required', 'success': False}), 400
        
        print(f"Add comment - Post: {post_id}, User: {username}, Text: {text[:50]}...")
        
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found', 'success': False}), 404
        
        user = get_or_create_user(username)
        
        comment = Comment(
            user_id=user.id,
            post_id=post.id,
            text=text.strip(),
            created_at=datetime.utcnow()
        )
        
        db.session.add(comment)
        post.comments_count += 1
        db.session.commit()
        
        print(f"Comment added successfully. ID: {comment.id}")
        
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
    
    except Exception as e:
        print(f"Error in add_comment: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/posts/<int:post_id>', methods=['GET'])
def get_post_details(post_id):
    """Get full details of a post"""
    try:
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found', 'success': False}), 404
        
        # Check if current user liked the post
        username = request.args.get('username', '')
        is_liked = False
        
        if username:
            user = User.query.filter_by(username=username).first()
            if user:
                like = Like.query.filter_by(user_id=user.id, post_id=post.id).first()
                is_liked = like is not None
        
        post_data = {
            'id': post.id,
            'username': post.user.username,
            'display_name': post.user.display_name,
            'image_url': post.image_url,
            'caption': post.caption,
            'created_at': post.created_at.isoformat(),
            'likes_count': post.likes_count,
            'comments_count': post.comments_count,
            'is_liked': is_liked
        }
        
        return jsonify({
            'success': True,
            'post': post_data
        })
    
    except Exception as e:
        print(f"Error in get_post_details: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500
