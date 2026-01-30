"""
فایل راه‌اندازی پایگاه داده
"""
import os
from app import app, db
from models import User, Post, Story, Comment, Like, Message, ChatRoom

print("ایجاد پایگاه داده و جدول‌ها...")

with app.app_context():
    # حذف فایل پایگاه داده قدیمی (اگر وجود دارد)
    if os.path.exists('social_media.db'):
        print("حذف پایگاه داده قدیمی...")
        os.remove('social_media.db')
    
    # ایجاد پوشه‌های لازم
    os.makedirs('static/uploads/posts', exist_ok=True)
    os.makedirs('static/uploads/stories', exist_ok=True)
    os.makedirs('static/uploads/profiles', exist_ok=True)
    
    # ایجاد جدول‌ها
    print("ایجاد جدول‌ها...")
    db.create_all()
    
    # ایجاد چند کاربر نمونه
    print("ایجاد کاربران نمونه...")
    users = [
        User(username='user1', display_name='کاربر یک'),
        User(username='user2', display_name='کاربر دو'),
        User(username='user3', display_name='کاربر سه'),
        User(username='test', display_name='کاربر تست'),
        User(username='admin', display_name='مدیر سیستم')
    ]
    
    for user in users:
        db.session.add(user)
    
    db.session.commit()
    
    print("پایگاه داده با موفقیت ایجاد شد!")
    print(f"تعداد کاربران: {len(users)}")
    print("نام‌کاربری‌های نمونه: user1, user2, user3, test, admin")
