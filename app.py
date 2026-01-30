from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename

# ساخت اپلیکیشن
app = Flask(__name__)
app.config['SECRET_KEY'] = 'instagram-clone-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instagram.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# ایجاد پوشه‌های آپلود
os.makedirs('static/uploads/posts', exist_ok=True)
os.makedirs('static/uploads/stories', exist_ok=True)
os.makedirs('static/uploads/profiles', exist_ok=True)

# راه‌اندازی دیتابیس و سوکت
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# مدل کاربر
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.Text, default='')
    profile_pic = db.Column(db.String(200), default='default_profile.jpg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    posts = db.relationship('Post', backref='author', lazy=True)
    stories = db.relationship('Story', backref='author', lazy=True)
    likes = db.relationship('Like', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    followers = db.relationship('Follow', foreign_keys='Follow.followed_id', backref='followed', lazy=True)
    following = db.relationship('Follow', foreign_keys='Follow.follower_id', backref='follower', lazy=True)
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    messages_received = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)

# مدل پست
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_url = db.Column(db.String(200), nullable=False)
    caption = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    likes = db.relationship('Like', backref='post', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')

# مدل استوری
class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_url = db.Column(db.String(200), nullable=False)
    media_type = db.Column(db.String(10), default='image')  # image or video
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# مدل لایک
class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_like'),)

# مدل کامنت
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# مدل فالو
class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('follower_id', 'followed_id', name='unique_follow'),)

# مدل پیام
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============ Helper Functions ============
def get_or_create_user(username):
    """دریافت کاربر یا ایجاد کاربر جدید"""
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(
            username=username,
            display_name=username,
            bio='کاربر جدید اینستاگرام'
        )
        db.session.add(user)
        db.session.commit()
    return user

def allowed_file(filename):
    """بررسی مجاز بودن فایل"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============ Routes ============
@app.route('/')
def home():
    """صفحه اصلی"""
    return render_template('index.html')

# ============ API Routes ============
@app.route('/api/init', methods=['POST'])
def init_app():
    """راه‌اندازی اولیه اپلیکیشن"""
    username = request.json.get('username')
    if not username:
        return jsonify({'success': False, 'error': 'نام کاربری الزامی است'})
    
    user = get_or_create_user(username)
    
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'display_name': user.display_name,
            'profile_pic': user.profile_pic
        }
    })

@app.route('/api/posts', methods=['GET'])
def get_posts():
    """دریافت پست‌ها"""
    posts = Post.query.order_by(Post.created_at.desc()).limit(20).all()
    
    posts_data = []
    for post in posts:
        post_data = {
            'id': post.id,
            'username': post.author.username,
            'display_name': post.author.display_name,
            'profile_pic': post.author.profile_pic,
            'image_url': post.image_url,
            'caption': post.caption,
            'created_at': post.created_at.isoformat(),
            'likes_count': Like.query.filter_by(post_id=post.id).count(),
            'comments_count': Comment.query.filter_by(post_id=post.id).count(),
            'is_liked': False  # بعداً بر اساس کاربر جاری تنظیم می‌شود
        }
        posts_data.append(post_data)
    
    return jsonify({'success': True, 'posts': posts_data})

@app.route('/api/posts/create', methods=['POST'])
def create_post():
    """ایجاد پست جدید"""
    try:
        username = request.form.get('username')
        caption = request.form.get('caption', '')
        
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'هیچ فایلی انتخاب نشده'})
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'هیچ فایلی انتخاب نشده'})
        
        if file and allowed_file(file.filename):
            user = get_or_create_user(username)
            
            # ذخیره فایل
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join('static/uploads/posts', unique_filename)
            file.save(filepath)
            
            # ایجاد پست
            post = Post(
                user_id=user.id,
                image_url=f'/static/uploads/posts/{unique_filename}',
                caption=caption
            )
            db.session.add(post)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'post': {
                    'id': post.id,
                    'image_url': post.image_url,
                    'caption': post.caption
                }
            })
        
        return jsonify({'success': False, 'error': 'فرمت فایل مجاز نیست'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
def toggle_like(post_id):
    """لایک/آنلایک پست"""
    try:
        username = request.json.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'نام کاربری الزامی است'})
        
        user = get_or_create_user(username)
        post = Post.query.get_or_404(post_id)
        
        # بررسی لایک قبلی
        existing_like = Like.query.filter_by(user_id=user.id, post_id=post_id).first()
        
        if existing_like:
            # آنلایک
            db.session.delete(existing_like)
            is_liked = False
        else:
            # لایک
            like = Like(user_id=user.id, post_id=post_id)
            db.session.add(like)
            is_liked = True
        
        db.session.commit()
        
        likes_count = Like.query.filter_by(post_id=post_id).count()
        
        return jsonify({
            'success': True,
            'is_liked': is_liked,
            'likes_count': likes_count
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/posts/<int:post_id>/comments', methods=['GET'])
def get_comments(post_id):
    """دریافت کامنت‌های پست"""
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.desc()).all()
    
    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'username': comment.author.username,
            'display_name': comment.author.display_name,
            'profile_pic': comment.author.profile_pic,
            'text': comment.text,
            'created_at': comment.created_at.isoformat()
        })
    
    return jsonify({'success': True, 'comments': comments_data})

@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
def add_comment(post_id):
    """افزودن کامنت"""
    try:
        username = request.json.get('username')
        text = request.json.get('text')
        
        if not username or not text:
            return jsonify({'success': False, 'error': 'نام کاربری و متن الزامی است'})
        
        user = get_or_create_user(username)
        post = Post.query.get_or_404(post_id)
        
        comment = Comment(
            user_id=user.id,
            post_id=post.id,
            text=text
        )
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'comment': {
                'id': comment.id,
                'username': user.username,
                'display_name': user.display_name,
                'profile_pic': user.profile_pic,
                'text': comment.text,
                'created_at': comment.created_at.isoformat()
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stories', methods=['GET'])
def get_stories():
    """دریافت استوری‌ها"""
    # استوری‌های 24 ساعت اخیر
    time_threshold = datetime.utcnow().timestamp() - 24 * 3600
    
    stories = Story.query.filter(Story.created_at > datetime.fromtimestamp(time_threshold))\
        .order_by(Story.created_at.desc()).all()
    
    # گروه‌بندی بر اساس کاربر
    stories_by_user = {}
    for story in stories:
        if story.user_id not in stories_by_user:
            stories_by_user[story.user_id] = {
                'user': {
                    'id': story.author.id,
                    'username': story.author.username,
                    'display_name': story.author.display_name,
                    'profile_pic': story.author.profile_pic
                },
                'stories': []
            }
        
        stories_by_user[story.user_id]['stories'].append({
            'id': story.id,
            'media_url': story.media_url,
            'media_type': story.media_type,
            'created_at': story.created_at.isoformat()
        })
    
    return jsonify({'success': True, 'stories': list(stories_by_user.values())})

@app.route('/api/stories/create', methods=['POST'])
def create_story():
    """ایجاد استوری جدید"""
    try:
        username = request.form.get('username')
        
        if 'media' not in request.files:
            return jsonify({'success': False, 'error': 'هیچ فایلی انتخاب نشده'})
        
        file = request.files['media']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'هیچ فایلی انتخاب نشده'})
        
        if file and allowed_file(file.filename):
            user = get_or_create_user(username)
            
            # تشخیص نوع فایل
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower()
            media_type = 'video' if ext in {'mp4', 'mov', 'avi'} else 'image'
            
            # ذخیره فایل
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join('static/uploads/stories', unique_filename)
            file.save(filepath)
            
            # ایجاد استوری
            story = Story(
                user_id=user.id,
                media_url=f'/static/uploads/stories/{unique_filename}',
                media_type=media_type
            )
            db.session.add(story)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'story': {
                    'id': story.id,
                    'media_url': story.media_url,
                    'media_type': story.media_type
                }
            })
        
        return jsonify({'success': False, 'error': 'فرمت فایل مجاز نیست'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/users/search', methods=['GET'])
def search_users():
    """جستجوی کاربران"""
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify({'success': True, 'users': []})
    
    users = User.query.filter(
        (User.username.ilike(f'%{query}%')) | 
        (User.display_name.ilike(f'%{query}%'))
    ).limit(10).all()
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'username': user.username,
            'display_name': user.display_name,
            'profile_pic': user.profile_pic
        })
    
    return jsonify({'success': True, 'users': users_data})

@app.route('/api/users/<username>', methods=['GET'])
def get_user_profile(username):
    """دریافت پروفایل کاربر"""
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'success': False, 'error': 'کاربر یافت نشد'})
    
    # آمار
    posts_count = Post.query.filter_by(user_id=user.id).count()
    followers_count = Follow.query.filter_by(followed_id=user.id).count()
    following_count = Follow.query.filter_by(follower_id=user.id).count()
    
    # پست‌های کاربر
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).limit(12).all()
    posts_data = []
    for post in posts:
        posts_data.append({
            'id': post.id,
            'image_url': post.image_url,
            'likes_count': Like.query.filter_by(post_id=post.id).count(),
            'comments_count': Comment.query.filter_by(post_id=post.id).count()
        })
    
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'display_name': user.display_name,
            'profile_pic': user.profile_pic,
            'bio': user.bio,
            'posts_count': posts_count,
            'followers_count': followers_count,
            'following_count': following_count
        },
        'posts': posts_data
    })

@app.route('/api/follow/<username>', methods=['POST'])
def toggle_follow(username):
    """دنبال کردن/آنفالو کردن"""
    try:
        current_username = request.json.get('current_user')
        if not current_username:
            return jsonify({'success': False, 'error': 'نام کاربری الزامی است'})
        
        current_user = get_or_create_user(current_username)
        target_user = User.query.filter_by(username=username).first()
        
        if not target_user:
            return jsonify({'success': False, 'error': 'کاربر یافت نشد'})
        
        # بررسی فالو قبلی
        existing_follow = Follow.query.filter_by(
            follower_id=current_user.id,
            followed_id=target_user.id
        ).first()
        
        if existing_follow:
            # آنفالو
            db.session.delete(existing_follow)
            is_following = False
        else:
            # فالو
            follow = Follow(
                follower_id=current_user.id,
                followed_id=target_user.id
            )
            db.session.add(follow)
            is_following = True
        
        db.session.commit()
        
        followers_count = Follow.query.filter_by(followed_id=target_user.id).count()
        
        return jsonify({
            'success': True,
            'is_following': is_following,
            'followers_count': followers_count
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============ Chat API ============
@app.route('/api/chat/users', methods=['GET'])
def get_chat_users():
    """دریافت لیست کاربران برای چت"""
    username = request.args.get('username')
    if not username:
        return jsonify({'success': False, 'error': 'نام کاربری الزامی است'})
    
    current_user = get_or_create_user(username)
    
    # کاربران غیر از خود کاربر
    users = User.query.filter(User.id != current_user.id).limit(20).all()
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'username': user.username,
            'display_name': user.display_name,
            'profile_pic': user.profile_pic
        })
    
    return jsonify({'success': True, 'users': users_data})

@app.route('/api/chat/messages', methods=['GET'])
def get_messages():
    """دریافت پیام‌های بین دو کاربر"""
    user1 = request.args.get('user1')
    user2 = request.args.get('user2')
    
    if not user1 or not user2:
        return jsonify({'success': False, 'error': 'هر دو کاربر الزامی هستند'})
    
    user1_obj = get_or_create_user(user1)
    user2_obj = get_or_create_user(user2)
    
    # دریافت پیام‌ها
    messages = Message.query.filter(
        ((Message.sender_id == user1_obj.id) & (Message.receiver_id == user2_obj.id)) |
        ((Message.sender_id == user2_obj.id) & (Message.receiver_id == user1_obj.id))
    ).order_by(Message.created_at.asc()).all()
    
    messages_data = []
    for msg in messages:
        messages_data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'receiver': msg.receiver.username,
            'content': msg.content,
            'is_read': msg.is_read,
            'created_at': msg.created_at.isoformat()
        })
    
    return jsonify({'success': True, 'messages': messages_data})

@app.route('/api/chat/send', methods=['POST'])
def send_message():
    """ارسال پیام"""
    try:
        sender = request.json.get('sender')
        receiver = request.json.get('receiver')
        content = request.json.get('content')
        
        if not all([sender, receiver, content]):
            return jsonify({'success': False, 'error': 'تمام فیلدها الزامی هستند'})
        
        sender_obj = get_or_create_user(sender)
        receiver_obj = get_or_create_user(receiver)
        
        message = Message(
            sender_id=sender_obj.id,
            receiver_id=receiver_obj.id,
            content=content
        )
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': {
                'id': message.id,
                'sender': sender,
                'receiver': receiver,
                'content': content,
                'created_at': message.created_at.isoformat()
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============ Socket.IO Events ============
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join_chat')
def handle_join_chat(data):
    username = data.get('username')
    room = data.get('room')
    
    if username and room:
        join_room(room)
        emit('user_joined', {'username': username, 'room': room}, room=room)

@socketio.on('send_chat_message')
def handle_chat_message(data):
    room = data.get('room')
    message = data.get('message')
    sender = data.get('sender')
    
    if room and message and sender:
        emit('new_message', {
            'sender': sender,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)

@socketio.on('typing')
def handle_typing(data):
    room = data.get('room')
    username = data.get('username')
    is_typing = data.get('is_typing')
    
    if room and username:
        emit('user_typing', {
            'username': username,
            'is_typing': is_typing
        }, room=room, include_self=False)

# ============ Main ============
@app.before_first_request
def create_tables():
    """ایجاد جداول دیتابیس"""
    db.create_all()
    
    # ایجاد کاربران نمونه
    sample_users = ['user1', 'user2', 'user3', 'user4', 'user5']
    for username in sample_users:
        if not User.query.filter_by(username=username).first():
            user = User(
                username=username,
                display_name=f'کاربر {username}',
                bio='به صفحه من خوش آمدید!'
            )
            db.session.add(user)
    
    db.session.commit()
    print("✅ دیتابیس و کاربران نمونه ایجاد شدند")

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
