#!/usr/bin/env python3
"""
InstaClone - Instagram Clone
راه‌اندازی سرور شبکه اجتماعی
"""

import os
import sys
from app import app, socketio, db
from app import User, Post, Story, Like, Comment, Follow, Message

def setup_database():
    """راه‌اندازی پایگاه داده"""
    print("📦 در حال راه‌اندازی پایگاه داده...")
    
    # ایجاد پوشه‌های لازم
    os.makedirs('static/uploads/posts', exist_ok=True)
    os.makedirs('static/uploads/stories', exist_ok=True)
    os.makedirs('static/uploads/profiles', exist_ok=True)
    
    # ایجاد جداول
    with app.app_context():
        db.create_all()
        print("✅ جداول دیتابیس ایجاد شدند")
        
        # ایجاد کاربران نمونه اگر وجود ندارند
        sample_users = ['user1', 'user2', 'user3', 'user4', 'user5']
        created_count = 0
        
        for username in sample_users:
            if not User.query.filter_by(username=username).first():
                user = User(
                    username=username,
                    display_name=f'کاربر {username}',
                    bio='به صفحه من در InstaClone خوش آمدید! 👋'
                )
                db.session.add(user)
                created_count += 1
        
        db.session.commit()
        
        if created_count > 0:
            print(f"✅ {created_count} کاربر نمونه ایجاد شدند")
        else:
            print("✅ کاربران نمونه از قبل وجود دارند")
        
        # ایجاد چند پست نمونه
        if Post.query.count() == 0:
            print("📸 در حال ایجاد پست‌های نمونه...")
            
            users = User.query.limit(3).all()
            sample_posts = [
                "اولین پست من در InstaClone! 🎉",
                "چه روز زیبایی! ☀️",
                "لحظات خوش با دوستان 📸"
            ]
            
            for i, user in enumerate(users):
                post = Post(
                    user_id=user.id,
                    image_url=f'https://picsum.photos/600/600?random={i}',
                    caption=sample_posts[i % len(sample_posts)]
                )
                db.session.add(post)
            
            db.session.commit()
            print("✅ پست‌های نمونه ایجاد شدند")

def main():
    """تابع اصلی اجرا"""
    print("=" * 50)
    print("🚀 InstaClone - شبکه اجتماعی اینستاگرام‌مانند")
    print("=" * 50)
    print("ویژگی‌ها:")
    print("✅ پست گذاشتن با عکس و کپشن")
    print("✅ استوری 24 ساعته")
    print("✅ لایک و کامنت روی پست‌ها")
    print("✅ چت آنلاین در لحظه")
    print("✅ دنبال کردن کاربران")
    print("✅ جستجوی کاربران")
    print("✅ طراحی واکنش‌گرا و زیبا")
    print("✅ بدون نیاز به ثبت‌نام (فقط نام کاربری)")
    print("=" * 50)
    
    # راه‌اندازی دیتابیس
    setup_database()
    
    # نمایش اطلاعات
    with app.app_context():
        user_count = User.query.count()
        post_count = Post.query.count()
        print(f"👥 تعداد کاربران: {user_count}")
        print(f"📸 تعداد پست‌ها: {post_count}")
    
    print("\n🌐 سرور در حال راه‌اندازی...")
    print("🔗 آدرس: http://localhost:5000")
    print("🛑 برای توقف سرور، Ctrl+C را فشار دهید")
    print("=" * 50)
    
    # اجرای سرور
    try:
        socketio.run(app, 
                    host='0.0.0.0', 
                    port=5000, 
                    debug=True,
                    use_reloader=True,
                    log_output=True)
    except KeyboardInterrupt:
        print("\n\n👋 سرور متوقف شد")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ خطا در اجرای سرور: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
