"""
Run script for the Social Media Platform
"""
from app import socketio, app

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
    print("Open http://localhost:5000 in your browser")
    print("=" * 60)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
