"""
Run script for the Social Media Platform
"""
import os
from app import socketio, app, db
from models import User

def init_database():
    """Initialize database if it doesn't exist"""
    database_path = 'social_media.db'
    
    if not os.path.exists(database_path):
        print("پایگاه داده یافت نشد. در حال ایجاد...")
        with app.app_context():
            # ایجاد جدول‌ها
            db.create_all()
            
            # ایجاد کاربران پیش‌فرض
            default_users = [
                User(username='user1', display_name='کاربر نمونه ۱'),
                User(username='user2', display_name='کاربر نمونه ۲'),
                User(username='user3', display_name='کاربر نمونه ۳')
            ]
            
            for user in default_users:
                if not User.query.filter_by(username=user.username).first():
                    db.session.add(user)
            
            db.session.commit()
            print(f"✅ پایگاه داده با {len(default_users)} کاربر نمونه ایجاد شد")
    else:
        print("✅ پایگاه داده موجود است")

if __name__ == '__main__':
    print("=" * 60)
    print("Social Media Platform - Instagram-like Application")
    print("=" * 60)
    print("Features:")
    print("- پست گذاشتن با عکس و کپشن")
    print("- گذاشتن استوری (تصویر/ویدیو)")
    print("- لایک و کامنت روی پست‌ها")
    print("- چت آنلاین در لحظه")
    print("- بدون نیاز به ثبت نام (فقط نام کاربری)")
    print("=" * 60)
    
    # راه‌اندازی پایگاه داده
    init_database()
    
    # نمایش اطلاعات
    with app.app_context():
        user_count = User.query.count()
        print(f"تعداد کاربران در سیستم: {user_count}")
        if user_count == 0:
            print("⚠️  هیچ کاربری در سیستم وجود ندارد")
            print("کاربران را با نام کاربری دلخواه ایجاد کنید")
    
    print("\nOpen http://localhost:5000 in your browser")
    print("=" * 60)
    
    # راه‌اندازی سرور
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
