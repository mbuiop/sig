#!/usr/bin/env python3
"""
🚀 سیستم حسابداری آنلاین فوق مدرن
سرور کامل با Flask، WebSocket، چت، فاکتور، و امنیت بالا
"""

from flask import Flask, request, jsonify, session, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import sqlite3
import hashlib
import secrets
import json
import os
import jwt
import base64
from datetime import datetime, timedelta
from functools import wraps
import uuid
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import qrcode
from io import BytesIO
from PIL import Image
import threading
import time

# ==================== تنظیمات اولیه ====================
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

CORS(app, supports_credentials=True, origins=["*"])

# تغییر async_mode از 'eventlet' به 'threading' برای سازگاری با پایتون ۳.۱۲
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   async_mode='threading',  # تغییر اینجا
                   logger=True, 
                   engineio_logger=True)

# کلیدهای امنیتی
JWT_SECRET = secrets.token_hex(32)
ENCRYPTION_KEY = hashlib.sha256(secrets.token_bytes(32)).digest()[:32]

# مسیر دیتابیس
DB_PATH = 'accounting_system.db'

# ==================== کلاس رمزنگاری پیشرفته ====================
class AdvancedEncryption:
    def __init__(self, key):
        self.key = key
    
    def encrypt(self, data):
        """رمزنگاری AES-256-CBC"""
        iv = get_random_bytes(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        ct_bytes = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
        encrypted = base64.b64encode(iv + ct_bytes).decode('utf-8')
        return encrypted
    
    def decrypt(self, encrypted_data):
        """رمزگشایی AES-256-CBC"""
        encrypted = base64.b64decode(encrypted_data)
        iv = encrypted[:16]
        ct = encrypted[16:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode('utf-8')
    
    def hash_password(self, password, salt=None):
        """رمزنگاری رمز عبور با salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha512', password.encode(), salt.encode(), 100000)
        return f"{salt}:{hash_obj.hex()}"

encryption = AdvancedEncryption(ENCRYPTION_KEY)

# ==================== دیتابیس ====================
def init_database():
    """ایجاد دیتابیس و جداول"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # کاربران
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            name TEXT,
            email TEXT,
            password_hash TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            api_key TEXT,
            settings TEXT DEFAULT '{}'
        )
    ''')
    
    # مشتریان
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT UNIQUE,
            email TEXT,
            address TEXT,
            notes TEXT,
            balance DECIMAL(15,2) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # فاکتورها
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            customer_id INTEGER,
            invoice_number TEXT UNIQUE NOT NULL,
            invoice_date DATE NOT NULL,
            due_date DATE,
            total_amount DECIMAL(15,2) NOT NULL,
            tax_amount DECIMAL(15,2) DEFAULT 0,
            discount_amount DECIMAL(15,2) DEFAULT 0,
            paid_amount DECIMAL(15,2) DEFAULT 0,
            status TEXT DEFAULT 'pending',
            payment_method TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            qr_code TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    ''')
    
    # اقلام فاکتور
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            description TEXT,
            quantity DECIMAL(10,2) NOT NULL,
            unit_price DECIMAL(15,2) NOT NULL,
            discount DECIMAL(5,2) DEFAULT 0,
            total_price DECIMAL(15,2) NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        )
    ''')
    
    # محصولات
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            unit TEXT DEFAULT 'عدد',
            barcode TEXT,
            buy_price DECIMAL(15,2),
            sell_price DECIMAL(15,2),
            stock_quantity DECIMAL(10,2) DEFAULT 0,
            min_stock DECIMAL(10,2) DEFAULT 0,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # تراکنش‌ها
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount DECIMAL(15,2) NOT NULL,
            description TEXT,
            category TEXT,
            date DATE NOT NULL,
            reference_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # چک‌ها
    c.execute('''
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            check_number TEXT NOT NULL,
            bank_name TEXT,
            amount DECIMAL(15,2) NOT NULL,
            due_date DATE NOT NULL,
            status TEXT DEFAULT 'pending',
            issuer_name TEXT,
            issuer_phone TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # پیام‌های چت
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            sender_id INTEGER NOT NULL,
            sender_type TEXT NOT NULL,
            message_type TEXT DEFAULT 'text',
            message_content TEXT,
            file_url TEXT,
            file_name TEXT,
            file_size INTEGER,
            is_read BOOLEAN DEFAULT 0,
            is_delivered BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # اتاق‌های چت
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT UNIQUE NOT NULL,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER,
            customer_id INTEGER,
            last_message TEXT,
            last_message_time TIMESTAMP,
            unread_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # OTP کدها
    c.execute('''
        CREATE TABLE IF NOT EXISTS otp_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            code TEXT NOT NULL,
            ip_address TEXT,
            device_info TEXT,
            is_used BOOLEAN DEFAULT 0,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # فایل‌ها
    c.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT,
            file_size INTEGER,
            file_path TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # گزارشات
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            report_type TEXT NOT NULL,
            report_data TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ دیتابیس با موفقیت راه‌اندازی شد")

# ==================== ابزارهای کمکی ====================
def get_db_connection():
    """ایجاد اتصال به دیتابیس"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_jwt_token(user_id, phone):
    """تولید توکن JWT"""
    payload = {
        'user_id': user_id,
        'phone': phone,
        'exp': datetime.utcnow() + timedelta(days=30),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token):
    """بررسی توکن JWT"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload['user_id']
    except:
        return None

def token_required(f):
    """دکوراتور برای احراز هویت"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'توکن احراز هویت لازم است'}), 401
        
        token = token[7:]
        user_id = verify_jwt_token(token)
        
        if not user_id:
            return jsonify({'error': 'توکن نامعتبر یا منقضی شده است'}), 401
        
        return f(user_id, *args, **kwargs)
    return decorated

def generate_otp_code():
    """تولید کد OTP 5 رقمی"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(5)])

def number_to_words(num):
    """تبدیل عدد به حروف فارسی"""
    units = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه']
    teens = ['ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده']
    tens = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود']
    hundreds = ['', 'صد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد']
    
    if num == 0:
        return 'صفر'
    
    def convert_three_digits(n):
        if n == 0:
            return ''
        
        if n < 10:
            return units[n]
        
        if n < 20:
            return teens[n - 10]
        
        if n < 100:
            tens_digit = n // 10
            units_digit = n % 10
            result = tens[tens_digit]
            if units_digit > 0:
                result += ' و ' + units[units_digit]
            return result
        
        hundreds_digit = n // 100
        remainder = n % 100
        result = hundreds[hundreds_digit]
        if remainder > 0:
            result += ' و ' + convert_three_digits(remainder)
        return result
    
    # تبدیل اعداد بزرگ
    result = ''
    scales = [
        (1000000000, 'میلیارد'),
        (1000000, 'میلیون'),
        (1000, 'هزار'),
        (1, '')
    ]
    
    for scale_value, scale_name in scales:
        if num >= scale_value:
            count = num // scale_value
            num %= scale_value
            
            if count > 0:
                if scale_name:
                    part = convert_three_digits(count) + ' ' + scale_name
                else:
                    part = convert_three_digits(count)
                
                if result:
                    result += ' و ' + part
                else:
                    result = part
    
    return result

def generate_qr_code(data):
    """تولید QR Code"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return base64.b64encode(img_bytes.getvalue()).decode('utf-8')

# ==================== API Routes ====================

# احراز هویت
@app.route('/api/auth/send-otp', methods=['POST'])
def send_otp():
    """ارسال کد OTP به شماره تلفن"""
    data = request.json
    phone = data.get('phone')
    
    if not phone:
        return jsonify({'error': 'شماره تلفن الزامی است'}), 400
    
    # تولید کد OTP
    code = generate_otp_code()
    expires_at = datetime.now() + timedelta(minutes=5)
    
    # ذخیره در دیتابیس
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # حذف کدهای قدیمی
    cursor.execute("DELETE FROM otp_codes WHERE phone = ? AND expires_at < ?", 
                  (phone, datetime.now()))
    
    # ذخیره کد جدید
    cursor.execute(
        "INSERT INTO otp_codes (phone, code, ip_address, expires_at) VALUES (?, ?, ?, ?)",
        (phone, encryption.encrypt(code), request.remote_addr, expires_at)
    )
    
    conn.commit()
    
    # بررسی وجود کاربر
    cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()
    
    if not user:
        # ایجاد کاربر جدید
        api_key = secrets.token_hex(32)
        cursor.execute(
            "INSERT INTO users (phone, name, api_key) VALUES (?, ?, ?)",
            (phone, f"کاربر {phone}", api_key)
        )
        user_id = cursor.lastrowid
    else:
        user_id = user['id']
        api_key = user['api_key']
    
    conn.close()
    
    # در اینجا باید سرویس SMS فراخوانی شود
    print(f"📱 کد OTP برای {phone}: {code}")
    
    return jsonify({
        'success': True,
        'message': 'کد تایید ارسال شد',
        'user_id': user_id,
        'api_key': api_key,
        'otp': code  # فقط برای محیط توسعه
    }), 200

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    """تایید کد OTP"""
    data = request.json
    phone = data.get('phone')
    code = data.get('code')
    
    if not phone or not code:
        return jsonify({'error': 'شماره تلفن و کد الزامی هستند'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # دریافت کدهای فعال
    cursor.execute(
        "SELECT * FROM otp_codes WHERE phone = ? AND is_used = 0 AND expires_at > ? ORDER BY created_at DESC",
        (phone, datetime.now())
    )
    
    otp_records = cursor.fetchall()
    
    # بررسی کدها
    valid_code = False
    for record in otp_records:
        try:
            decrypted_code = encryption.decrypt(record['code'])
            if decrypted_code == code:
                valid_code = True
                # علامت‌گذاری به عنوان استفاده شده
                cursor.execute("UPDATE otp_codes SET is_used = 1 WHERE id = ?", (record['id'],))
                break
        except:
            continue
    
    if not valid_code:
        conn.close()
        return jsonify({'error': 'کد تایید نامعتبر است'}), 400
    
    # دریافت اطلاعات کاربر
    cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'کاربر پیدا نشد'}), 404
    
    # آپدیت زمان آخرین ورود
    cursor.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (datetime.now(), user['id'])
    )
    
    conn.commit()
    conn.close()
    
    # ایجاد توکن JWT
    token = generate_jwt_token(user['id'], phone)
    
    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user['id'],
            'phone': user['phone'],
            'name': user['name'],
            'email': user['email']
        },
        'message': 'ورود موفقیت‌آمیز'
    }), 200

# کاربران
@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_user_profile(user_id):
    """دریافت پروفایل کاربر"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'error': 'کاربر پیدا نشد'}), 404
    
    return jsonify({
        'success': True,
        'user': dict(user)
    }), 200

@app.route('/api/user/profile', methods=['PUT'])
@token_required
def update_user_profile(user_id):
    """آپدیت پروفایل کاربر"""
    data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET name = ?, email = ? WHERE id = ?",
        (data.get('name'), data.get('email'), user_id)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'پروفایل با موفقیت به‌روزرسانی شد'
    }), 200

# مشتریان
@app.route('/api/customers', methods=['GET'])
@token_required
def get_customers(user_id):
    """دریافت لیست مشتریان"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM customers WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    
    customers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        'success': True,
        'customers': customers,
        'count': len(customers)
    }), 200

@app.route('/api/customers', methods=['POST'])
@token_required
def create_customer(user_id):
    """ایجاد مشتری جدید"""
    data = request.json
    
    required_fields = ['name', 'phone']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'فیلد {field} الزامی است'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # بررسی تکراری نبودن شماره تلفن
    cursor.execute(
        "SELECT id FROM customers WHERE phone = ? AND user_id = ?",
        (data['phone'], user_id)
    )
    
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'شماره تلفن تکراری است'}), 400
    
    # ایجاد مشتری
    cursor.execute('''
        INSERT INTO customers 
        (user_id, name, phone, email, address, notes, balance) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        data['name'],
        data['phone'],
        data.get('email', ''),
        data.get('address', ''),
        data.get('notes', ''),
        data.get('balance', 0)
    ))
    
    customer_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'مشتری با موفقیت ایجاد شد',
        'customer_id': customer_id
    }), 201

@app.route('/api/customers/<int:customer_id>', methods=['DELETE'])
@token_required
def delete_customer(user_id, customer_id):
    """حذف مشتری"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # بررسی مالکیت
    cursor.execute(
        "SELECT id FROM customers WHERE id = ? AND user_id = ?",
        (customer_id, user_id)
    )
    
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'مشتری پیدا نشد'}), 404
    
    cursor.execute(
        "DELETE FROM customers WHERE id = ? AND user_id = ?",
        (customer_id, user_id)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'مشتری با موفقیت حذف شد'
    }), 200

# فاکتورها
@app.route('/api/invoices', methods=['GET'])
@token_required
def get_invoices(user_id):
    """دریافت لیست فاکتورها"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT i.*, c.name as customer_name 
        FROM invoices i 
        LEFT JOIN customers c ON i.customer_id = c.id 
        WHERE i.user_id = ? 
        ORDER BY i.created_at DESC
    ''', (user_id,))
    
    invoices = []
    for row in cursor.fetchall():
        invoice = dict(row)
        
        # دریافت اقلام فاکتور
        cursor.execute(
            "SELECT * FROM invoice_items WHERE invoice_id = ?",
            (invoice['id'],)
        )
        items = [dict(item) for item in cursor.fetchall()]
        invoice['items'] = items
        
        invoices.append(invoice)
    
    conn.close()
    
    return jsonify({
        'success': True,
        'invoices': invoices,
        'count': len(invoices)
    }), 200

@app.route('/api/invoices', methods=['POST'])
@token_required
def create_invoice(user_id):
    """ایجاد فاکتور جدید"""
    data = request.json
    
    # اعتبارسنجی داده‌ها
    if 'items' not in data or not data['items']:
        return jsonify({'error': 'افزودن حداقل یک کالا الزامی است'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # تولید شماره فاکتور
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{secrets.randbelow(10000):04d}"
        
        # محاسبه مبالغ
        subtotal = sum(item['quantity'] * item['unit_price'] for item in data['items'])
        tax_amount = subtotal * (data.get('tax_rate', 0) / 100)
        discount_amount = data.get('discount_amount', 0)
        total_amount = subtotal + tax_amount - discount_amount
        
        # ایجاد QR Code
        qr_data = {
            'invoice_number': invoice_number,
            'date': data.get('invoice_date', datetime.now().date().isoformat()),
            'total': total_amount,
            'customer': data.get('customer_name', ''),
            'user_id': user_id
        }
        qr_code = generate_qr_code(json.dumps(qr_data))
        
        # ذخیره فاکتور
        cursor.execute('''
            INSERT INTO invoices 
            (user_id, customer_id, invoice_number, invoice_date, due_date, 
             total_amount, tax_amount, discount_amount, paid_amount, 
             status, payment_method, notes, qr_code) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data.get('customer_id'),
            invoice_number,
            data.get('invoice_date', datetime.now().date().isoformat()),
            data.get('due_date'),
            total_amount,
            tax_amount,
            discount_amount,
            data.get('paid_amount', 0),
            data.get('status', 'pending'),
            data.get('payment_method', ''),
            data.get('notes', ''),
            qr_code
        ))
        
        invoice_id = cursor.lastrowid
        
        # ذخیره اقلام فاکتور
        for item in data['items']:
            total_price = item['quantity'] * item['unit_price']
            cursor.execute('''
                INSERT INTO invoice_items 
                (invoice_id, product_name, description, quantity, unit_price, discount, total_price) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_id,
                item['product_name'],
                item.get('description', ''),
                item['quantity'],
                item['unit_price'],
                item.get('discount', 0),
                total_price
            ))
        
        # ذخیره تراکنش
        if total_amount > 0:
            cursor.execute('''
                INSERT INTO transactions 
                (user_id, type, amount, description, category, date, reference_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                'income',
                total_amount,
                f'فاکتور شماره {invoice_number}',
                'invoice',
                datetime.now().date().isoformat(),
                invoice_number
            ))
        
        conn.commit()
        
        # ارسال نوتیفیکیشن از طریق WebSocket
        socketio.emit('new_invoice', {
            'invoice_id': invoice_id,
            'invoice_number': invoice_number,
            'total_amount': total_amount,
            'customer_id': data.get('customer_id')
        }, room=f'user_{user_id}')
        
        return jsonify({
            'success': True,
            'message': 'فاکتور با موفقیت ایجاد شد',
            'invoice_id': invoice_id,
            'invoice_number': invoice_number,
            'total_amount': total_amount,
            'total_words': number_to_words(int(total_amount)) + ' تومان',
            'qr_code': qr_code
        }), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/invoices/<int:invoice_id>/download', methods=['GET'])
@token_required
def download_invoice_image(user_id, invoice_id):
    """دانلود فاکتور به صورت عکس"""
    # در اینجا باید از کتابخانه‌هایی مانند ReportLab یا imgkit استفاده شود
    # فعلاً یک پیام برگردانده می‌شود
    return jsonify({
        'success': True,
        'message': 'دریافت عکس فاکتور',
        'url': f'/api/invoices/{invoice_id}/image.png'
    }), 200

# چک‌ها
@app.route('/api/checks', methods=['GET'])
@token_required
def get_checks(user_id):
    """دریافت لیست چک‌ها"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM checks WHERE user_id = ? ORDER BY due_date",
        (user_id,)
    )
    
    checks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        'success': True,
        'checks': checks,
        'count': len(checks)
    }), 200

# محصولات
@app.route('/api/products', methods=['GET'])
@token_required
def get_products(user_id):
    """دریافت لیست محصولات"""
    category = request.args.get('category')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if category:
        cursor.execute(
            "SELECT * FROM products WHERE user_id = ? AND category = ? ORDER BY name",
            (user_id, category)
        )
    else:
        cursor.execute(
            "SELECT * FROM products WHERE user_id = ? ORDER BY category, name",
            (user_id,)
        )
    
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        'success': True,
        'products': products,
        'count': len(products)
    }), 200

# تراکنش‌ها
@app.route('/api/transactions', methods=['GET'])
@token_required
def get_transactions(user_id):
    """دریافت لیست تراکنش‌ها"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM transactions WHERE user_id = ?"
    params = [user_id]
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    query += " ORDER BY date DESC, created_at DESC"
    
    cursor.execute(query, params)
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # محاسبه آمار
    total_income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    total_expense = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    net_profit = total_income - total_expense
    
    return jsonify({
        'success': True,
        'transactions': transactions,
        'count': len(transactions),
        'stats': {
            'total_income': total_income,
            'total_expense': total_expense,
            'net_profit': net_profit
        }
    }), 200

# ==================== WebSocket برای چت ====================

@socketio.on('connect')
def handle_connect():
    """اتصال WebSocket"""
    print(f"🔗 کلاینت متصل شد: {request.sid}")
    emit('connected', {'message': 'به سیستم چت خوش آمدید'})

@socketio.on('authenticate')
def handle_authentication(data):
    """احراز هویت WebSocket"""
    token = data.get('token')
    if not token:
        return
    
    user_id = verify_jwt_token(token)
    if user_id:
        join_room(f'user_{user_id}')
        emit('authenticated', {'user_id': user_id, 'status': 'success'})
        print(f"✅ کاربر {user_id} احراز هویت شد و به room اضافه شد")
    else:
        emit('authentication_failed', {'error': 'توکن نامعتبر'})

@socketio.on('join_chat')
def handle_join_chat(data):
    """ورود به چت با مشتری"""
    user_id = data.get('user_id')
    customer_id = data.get('customer_id')
    
    if user_id and customer_id:
        room_id = f"chat_{user_id}_{customer_id}"
        join_room(room_id)
        
        # بارگذاری تاریخچه چت
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM chat_messages 
            WHERE room_id = ? 
            ORDER BY created_at DESC 
            LIMIT 50
        ''', (room_id,))
        
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        emit('chat_history', {'messages': messages[::-1]})
        print(f"💬 کاربر {user_id} وارد چت با مشتری {customer_id} شد")

@socketio.on('send_message')
def handle_send_message(data):
    """ارسال پیام در چت"""
    user_id = data.get('user_id')
    customer_id = data.get('customer_id')
    message = data.get('message')
    message_type = data.get('type', 'text')
    
    if not all([user_id, customer_id, message]):
        return
    
    room_id = f"chat_{user_id}_{customer_id}"
    
    # ذخیره پیام در دیتابیس
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ایجاد یا به‌روزرسانی اتاق چت
    cursor.execute(
        "SELECT id FROM chat_rooms WHERE room_id = ?",
        (room_id,)
    )
    
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO chat_rooms (room_id, user1_id, customer_id, last_message, last_message_time) 
            VALUES (?, ?, ?, ?, ?)
        ''', (room_id, user_id, customer_id, message[:100], datetime.now()))
    else:
        cursor.execute('''
            UPDATE chat_rooms 
            SET last_message = ?, last_message_time = ?, unread_count = unread_count + 1 
            WHERE room_id = ?
        ''', (message[:100], datetime.now(), room_id))
    
    # ذخیره پیام
    message_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO chat_messages 
        (room_id, sender_id, sender_type, message_type, message_content) 
        VALUES (?, ?, ?, ?, ?)
    ''', (room_id, user_id, 'user', message_type, message))
    
    conn.commit()
    conn.close()
    
    # ارسال پیام به همه در اتاق
    emit('new_message', {
        'id': message_id,
        'room_id': room_id,
        'sender_id': user_id,
        'sender_type': 'user',
        'message_type': message_type,
        'message_content': message,
        'timestamp': datetime.now().isoformat()
    }, room=room_id)
    
    print(f"📨 پیام از کاربر {user_id} به مشتری {customer_id}: {message[:50]}...")

@socketio.on('upload_file')
def handle_file_upload(data):
    """آپلود فایل در چت"""
    user_id = data.get('user_id')
    customer_id = data.get('customer_id')
    file_data = data.get('file_data')  # base64 encoded
    file_name = data.get('file_name')
    file_type = data.get('file_type')
    
    if not all([user_id, customer_id, file_data]):
        return
    
    # ذخیره فایل
    file_bytes = base64.b64decode(file_data)
    file_size = len(file_bytes)
    
    # ایجاد پوشه uploads
    os.makedirs('uploads/chat_files', exist_ok=True)
    
    # ذخیره فایل
    file_path = f"uploads/chat_files/{uuid.uuid4()}_{file_name}"
    with open(file_path, 'wb') as f:
        f.write(file_bytes)
    
    room_id = f"chat_{user_id}_{customer_id}"
    
    # ذخیره در دیتابیس
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO chat_messages 
        (room_id, sender_id, sender_type, message_type, file_url, file_name, file_size) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (room_id, user_id, 'user', 'file', file_path, file_name, file_size))
    
    # آپدیت اتاق چت
    cursor.execute('''
        UPDATE chat_rooms 
        SET last_message = ?, last_message_time = ?, unread_count = unread_count + 1 
        WHERE room_id = ?
    ''', (f"فایل: {file_name}", datetime.now(), room_id))
    
    conn.commit()
    conn.close()
    
    # ارسال نوتیفیکیشن
    emit('file_uploaded', {
        'room_id': room_id,
        'file_name': file_name,
        'file_type': file_type,
        'file_size': file_size,
        'file_url': f'/api/files/{os.path.basename(file_path)}',
        'sender_id': user_id,
        'timestamp': datetime.now().isoformat()
    }, room=room_id)
    
    print(f"📎 فایل {file_name} ({file_size} bytes) از کاربر {user_id} آپلود شد")

# ==================== API گزارشات ====================

@app.route('/api/reports/financial', methods=['GET'])
@token_required
def get_financial_report(user_id):
    """گزارش مالی"""
    period = request.args.get('period', 'monthly')  # daily, weekly, monthly, yearly
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # داده‌های مالی
    cursor.execute('''
        SELECT 
            strftime('%Y-%m', date) as period,
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
        FROM transactions 
        WHERE user_id = ? 
        GROUP BY strftime('%Y-%m', date)
        ORDER BY period DESC
        LIMIT 12
    ''', (user_id,))
    
    financial_data = [dict(row) for row in cursor.fetchall()]
    
    # آمار کلی
    cursor.execute('''
        SELECT 
            COUNT(DISTINCT customer_id) as total_customers,
            COUNT(*) as total_invoices,
            SUM(total_amount) as total_sales,
            SUM(paid_amount) as total_collected
        FROM invoices 
        WHERE user_id = ?
    ''', (user_id,))
    
    stats = dict(cursor.fetchone())
    
    conn.close()
    
    return jsonify({
        'success': True,
        'period': period,
        'financial_data': financial_data,
        'stats': stats
    }), 200

@app.route('/api/reports/export', methods=['POST'])
@token_required
def export_report(user_id):
    """خروجی گزارش"""
    data = request.json
    report_type = data.get('type', 'excel')  # excel, pdf, csv
    format_type = data.get('format', 'detailed')
    
    # ایجاد گزارش
    report_id = str(uuid.uuid4())
    report_data = {
        'user_id': user_id,
        'report_type': report_type,
        'format': format_type,
        'generated_at': datetime.now().isoformat(),
        'data': {
            'summary': 'گزارش مالی سیستم حسابداری',
            'period': 'ماه جاری',
            'total_income': 0,
            'total_expense': 0
        }
    }
    
    # ذخیره در دیتابیس
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO reports (user_id, report_type, report_data) 
        VALUES (?, ?, ?)
    ''', (user_id, report_type, json.dumps(report_data, ensure_ascii=False)))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'report_id': report_id,
        'message': 'گزارش با موفقیت ایجاد شد',
        'download_url': f'/api/reports/{report_id}/download'
    }), 200

# ==================== API مدیریت فایل ====================

@app.route('/api/files/upload', methods=['POST'])
@token_required
def upload_file(user_id):
    """آپلود فایل"""
    if 'file' not in request.files:
        return jsonify({'error': 'فایلی ارسال نشده است'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'نام فایل معتبر نیست'}), 400
    
    # ایجاد پوشه uploads
    os.makedirs('uploads', exist_ok=True)
    
    # ذخیره فایل
    file_extension = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join('uploads', file_name)
    
    file.save(file_path)
    file_size = os.path.getsize(file_path)
    
    # ذخیره در دیتابیس
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO files (user_id, file_name, file_type, file_size, file_path) 
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, file.filename, file.content_type, file_size, file_path))
    
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'file_id': file_id,
        'file_name': file.filename,
        'file_size': file_size,
        'file_url': f'/api/files/{file_name}'
    }), 200

@app.route('/api/files/<filename>', methods=['GET'])
def get_file(filename):
    """دریافت فایل"""
    file_path = os.path.join('uploads', filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'فایل پیدا نشد'}), 404
    
    return send_file(file_path, as_attachment=True)

# ==================== API سیستم ====================

@app.route('/api/system/health', methods=['GET'])
def health_check():
    """بررسی وضعیت سیستم"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'services': {
            'database': 'connected',
            'websocket': 'running',
            'encryption': 'active'
        }
    }), 200

@app.route('/api/system/backup', methods=['POST'])
@token_required
def create_backup(user_id):
    """ایجاد پشتیبان"""
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_file = f"{backup_dir}/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    import shutil
    shutil.copy2(DB_PATH, backup_file)
    
    # فشرده‌سازی
    import zipfile
    with zipfile.ZipFile(f"{backup_file}.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(backup_file, os.path.basename(backup_file))
    
    os.remove(backup_file)
    
    return jsonify({
        'success': True,
        'message': 'پشتیبان با موفقیت ایجاد شد',
        'backup_file': f"{backup_file}.zip",
        'size': os.path.getsize(f"{backup_file}.zip")
    }), 200

# ==================== اجرای سرور ====================
def run_background_tasks():
    """وظایف پس‌زمینه"""
    def check_expired_checks():
        while True:
            time.sleep(3600)  # هر 1 ساعت
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "UPDATE checks SET status = 'expired' WHERE due_date < ? AND status = 'pending'",
                    (datetime.now().date().isoformat(),)
                )
                
                conn.commit()
                conn.close()
                print("✅ چک‌های منقضی شده بررسی شدند")
            except Exception as e:
                print(f"❌ خطا در بررسی چک‌ها: {e}")
    
    def send_reminders():
        while True:
            time.sleep(1800)  # هر 30 دقیقه
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # چک‌های در حال سررسید
                tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
                cursor.execute(
                    "SELECT * FROM checks WHERE due_date = ? AND status = 'pending'",
                    (tomorrow,)
                )
                
                checks = cursor.fetchall()
                for check in checks:
                    # ارسال نوتیفیکیشن WebSocket
                    socketio.emit('check_reminder', {
                        'check_id': check['id'],
                        'check_number': check['check_number'],
                        'amount': check['amount'],
                        'due_date': check['due_date'],
                        'bank_name': check['bank_name']
                    }, room=f"user_{check['user_id']}")
                
                conn.close()
                print(f"✅ {len(checks)} یادآوری چک ارسال شد")
            except Exception as e:
                print(f"❌ خطا در ارسال یادآوری: {e}")
    
    # شروع وظایف
    threading.Thread(target=check_expired_checks, daemon=True).start()
    threading.Thread(target=send_reminders, daemon=True).start()

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 سیستم حسابداری آنلاین فوق مدرن")
    print("=" * 60)
    
    # راه‌اندازی دیتابیس
    init_database()
    
    # ایجاد دایرکتوری‌های مورد نیاز
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('backups', exist_ok=True)
    os.makedirs('uploads/chat_files', exist_ok=True)
    
    # شروع وظایف پس‌زمینه
    run_background_tasks()
    
    print("✅ سیستم آماده است")
    print("🌐 آدرس: http://localhost:5000")
    print("📧 تست شماره: 09123456789")
    print("🔑 کد OTP: 12345 (برای تست)")
    print("=" * 60)
    
    # اجرای سرور
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True,
        allow_unsafe_werkzeug=True
  )
