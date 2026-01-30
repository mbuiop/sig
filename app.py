#!/usr/bin/env python3
"""
🏦 سیستم حسابداری مدرن - Modern Accounting System
با قابلیت ثبت‌نام با هر شماره تلفن و پنل مدیریت کامل
"""

from flask import Flask, request, jsonify, render_template_string
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

# تنظیم CORS کامل
CORS(app, 
     resources={r"/*": {"origins": "*"}},
     supports_credentials=True,
     allow_headers=["*"],
     methods=["*"])

socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='threading',
                   logger=False)

# کلیدهای امنیتی
JWT_SECRET = secrets.token_hex(32)
ENCRYPTION_KEY = hashlib.sha256(b"accounting_system_key").digest()[:32]

# مسیر دیتابیس
DB_PATH = 'modern_accounting.db'

# ==================== رفع CORS ====================
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@app.route('/api/test', methods=['GET', 'OPTIONS'])
def test_api():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    return jsonify({
        'success': True,
        'message': '✅ سرور فعال است',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

# ==================== کلاس رمزنگاری ====================
class Security:
    def __init__(self):
        self.key = ENCRYPTION_KEY
    
    def encrypt(self, text):
        """رمزنگاری متن"""
        iv = get_random_bytes(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        ct_bytes = cipher.encrypt(pad(text.encode(), AES.block_size))
        return base64.b64encode(iv + ct_bytes).decode()
    
    def decrypt(self, enc_text):
        """رمزگشایی متن"""
        enc = base64.b64decode(enc_text)
        iv = enc[:16]
        ct = enc[16:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode()

security = Security()

# ==================== دیتابیس ====================
def init_db():
    """ایجاد جداول دیتابیس"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # کاربران
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            full_name TEXT,
            email TEXT,
            business_name TEXT,
            business_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            settings TEXT DEFAULT '{}'
        )
    ''')
    
    # OTP ها
    c.execute('''
        CREATE TABLE IF NOT EXISTS otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            code TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # مشتریان
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            customer_type TEXT DEFAULT 'retail',
            balance DECIMAL(15,2) DEFAULT 0,
            credit_limit DECIMAL(15,2) DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # محصولات/خدمات
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            unit TEXT DEFAULT 'عدد',
            price DECIMAL(15,2) NOT NULL,
            cost DECIMAL(15,2),
            stock INTEGER DEFAULT 0,
            barcode TEXT,
            image_url TEXT,
            is_active BOOLEAN DEFAULT 1,
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
            subtotal DECIMAL(15,2) DEFAULT 0,
            tax_amount DECIMAL(15,2) DEFAULT 0,
            discount_amount DECIMAL(15,2) DEFAULT 0,
            total_amount DECIMAL(15,2) NOT NULL,
            paid_amount DECIMAL(15,2) DEFAULT 0,
            remaining_amount DECIMAL(15,2) DEFAULT 0,
            status TEXT DEFAULT 'pending',
            payment_method TEXT,
            notes TEXT,
            qr_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    ''')
    
    # اقلام فاکتور
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            description TEXT,
            quantity DECIMAL(10,3) NOT NULL,
            unit_price DECIMAL(15,2) NOT NULL,
            discount_percent DECIMAL(5,2) DEFAULT 0,
            tax_percent DECIMAL(5,2) DEFAULT 0,
            total_price DECIMAL(15,2) NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id)
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
            payment_method TEXT,
            status TEXT DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # گزارشات مالی
    c.execute('''
        CREATE TABLE IF NOT EXISTS financial_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            report_type TEXT NOT NULL,
            period TEXT,
            start_date DATE,
            end_date DATE,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ دیتابیس مدرن ایجاد شد")

# ==================== ابزارهای کمکی ====================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_otp():
    """تولید کد ۵ رقمی"""
    return str(secrets.randbelow(90000) + 10000)

def generate_token(user_id, phone):
    """تولید JWT Token"""
    payload = {
        'user_id': user_id,
        'phone': phone,
        'exp': datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_token(token):
    """بررسی JWT Token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload['user_id']
    except:
        return None

def token_required(f):
    """دکوراتور برای APIهای نیازمند توکن"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'توکن لازم است'}), 401
        
        user_id = verify_token(token[7:])
        if not user_id:
            return jsonify({'error': 'توکن نامعتبر'}), 401
        
        return f(user_id, *args, **kwargs)
    return decorated

def number_to_words(num):
    """تبدیل عدد به حروف فارسی"""
    # ساده‌سازی شده - در نسخه کامل می‌توانید پیاده‌سازی کامل‌تری داشته باشید
    units = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه']
    tens = ['', 'ده', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود']
    
    if num == 0:
        return 'صفر'
    
    result = ''
    if num >= 1000000000:
        result += units[num // 1000000000] + ' میلیارد و '
        num %= 1000000000
    
    if num >= 1000000:
        result += units[num // 1000000] + ' میلیون و '
        num %= 1000000
    
    if num >= 1000:
        result += units[num // 1000] + ' هزار و '
        num %= 1000
    
    if num >= 100:
        result += units[num // 100] + ' صد و '
        num %= 100
    
    if num >= 10:
        result += tens[num // 10] + ' و '
        num %= 10
    
    if num > 0:
        result += units[num]
    
    return result.rstrip(' و ') + ' تومان'

def generate_qr(data):
    """تولید QR Code"""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# ==================== صفحه اصلی (SPA مدرن) ====================
@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🏦 سیستم حسابداری مدرن</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }
            .container {
                max-width: 400px;
                margin: 0 auto;
                padding: 20px;
            }
            .auth-box {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                margin-top: 100px;
                text-align: center;
                box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            }
            .logo { font-size: 60px; margin-bottom: 20px; }
            h1 { margin-bottom: 10px; font-size: 28px; }
            .subtitle {
                margin-bottom: 30px;
                opacity: 0.8;
                font-size: 16px;
            }
            .phone-input {
                width: 100%;
                padding: 15px;
                border: none;
                border-radius: 50px;
                background: rgba(255, 255, 255, 0.15);
                color: white;
                font-size: 18px;
                text-align: center;
                margin-bottom: 20px;
                outline: none;
            }
            .phone-input::placeholder {
                color: rgba(255, 255, 255, 0.6);
            }
            .btn {
                width: 100%;
                padding: 16px;
                border: none;
                border-radius: 50px;
                background: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
                color: white;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s;
                margin-bottom: 15px;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            }
            .otp-inputs {
                display: flex;
                gap: 10px;
                margin: 25px 0;
                justify-content: center;
            }
            .otp-input {
                width: 50px;
                height: 50px;
                text-align: center;
                font-size: 22px;
                border: none;
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.15);
                color: white;
                outline: none;
            }
            .timer {
                margin: 15px 0;
                font-size: 14px;
                opacity: 0.8;
            }
            .message {
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: center;
                display: none;
            }
            .success {
                background: rgba(76, 175, 80, 0.2);
                border: 1px solid #4CAF50;
                display: block;
            }
            .error {
                background: rgba(244, 67, 54, 0.2);
                border: 1px solid #F44336;
                display: block;
            }
            .loading {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid rgba(255,255,255,0.3);
                border-radius: 50%;
                border-top-color: white;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            .footer {
                margin-top: 30px;
                font-size: 12px;
                opacity: 0.6;
                text-align: center;
            }
            .dashboard {
                display: none;
                padding: 20px;
            }
            .dashboard-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding: 20px;
                background: rgba(255,255,255,0.1);
                border-radius: 15px;
            }
            .welcome-text {
                font-size: 24px;
                font-weight: bold;
            }
            .logout-btn {
                background: rgba(244, 67, 54, 0.2);
                color: #ff5252;
                padding: 10px 20px;
                border-radius: 25px;
                border: none;
                cursor: pointer;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: rgba(255,255,255,0.1);
                padding: 20px;
                border-radius: 15px;
                text-align: center;
            }
            .stat-value {
                font-size: 24px;
                font-weight: bold;
                margin: 10px 0;
                color: #4facfe;
            }
            .quick-actions {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
                margin-bottom: 30px;
            }
            .action-btn {
                background: rgba(255,255,255,0.1);
                padding: 20px;
                border-radius: 15px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
            }
            .action-btn:hover {
                background: rgba(255,255,255,0.2);
                transform: translateY(-5px);
            }
            .action-icon {
                font-size: 30px;
                margin-bottom: 10px;
            }
            .recent-list {
                background: rgba(255,255,255,0.1);
                padding: 20px;
                border-radius: 15px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div id="app">
            <!-- صفحه احراز هویت -->
            <div class="container" id="authContainer">
                <div class="auth-box">
                    <div class="logo">🏦</div>
                    <h1>سیستم حسابداری مدرن</h1>
                    <p class="subtitle">مدیریت مالی هوشمند برای کسب‌وکار شما</p>
                    
                    <div id="step1">
                        <input type="tel" class="phone-input" id="phoneInput" 
                               placeholder="شماره موبایل خود را وارد کنید" 
                               maxlength="11">
                        <button class="btn" onclick="sendOTP()">
                            <span>دریافت کد تایید</span>
                        </button>
                        <div class="footer">
                            با ادامه، شرایط و حریم خصوصی را می‌پذیرید
                        </div>
                    </div>
                    
                    <div id="step2" style="display: none;">
                        <p>کد ۵ رقمی به شماره <span id="phoneDisplay"></span> ارسال شد</p>
                        <div class="otp-inputs">
                            <input type="text" class="otp-input" maxlength="1" oninput="moveNext(1)">
                            <input type="text" class="otp-input" maxlength="1" oninput="moveNext(2)">
                            <input type="text" class="otp-input" maxlength="1" oninput="moveNext(3)">
                            <input type="text" class="otp-input" maxlength="1" oninput="moveNext(4)">
                            <input type="text" class="otp-input" maxlength="1" oninput="moveNext(5)">
                        </div>
                        <div class="timer" id="timer">۲:۰۰</div>
                        <button class="btn" onclick="verifyOTP()">تایید و ورود</button>
                        <button class="btn" style="background: rgba(255,255,255,0.1);" 
                                onclick="backToStep1()">تغییر شماره</button>
                    </div>
                    
                    <div id="message" class="message"></div>
                </div>
            </div>
            
            <!-- داشبورد -->
            <div class="dashboard" id="dashboard">
                <div class="dashboard-header">
                    <div>
                        <div class="welcome-text" id="welcomeText">خوش آمدید!</div>
                        <div id="userPhone"></div>
                    </div>
                    <button class="logout-btn" onclick="logout()">خروج</button>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div>موجودی</div>
                        <div class="stat-value" id="balance">۰ تومان</div>
                    </div>
                    <div class="stat-card">
                        <div>مشتریان</div>
                        <div class="stat-value" id="customersCount">۰</div>
                    </div>
                    <div class="stat-card">
                        <div>فاکتورها</div>
                        <div class="stat-value" id="invoicesCount">۰</div>
                    </div>
                    <div class="stat-card">
                        <div>درآمد ماه</div>
                        <div class="stat-value" id="monthlyIncome">۰ تومان</div>
                    </div>
                </div>
                
                <div class="quick-actions">
                    <div class="action-btn" onclick="showModal('newInvoice')">
                        <div class="action-icon">🧾</div>
                        <div>فاکتور جدید</div>
                    </div>
                    <div class="action-btn" onclick="showModal('newCustomer')">
                        <div class="action-icon">👥</div>
                        <div>مشتری جدید</div>
                    </div>
                    <div class="action-btn" onclick="showModal('newProduct')">
                        <div class="action-icon">📦</div>
                        <div>کالای جدید</div>
                    </div>
                    <div class="action-btn" onclick="showModal('transactions')">
                        <div class="action-icon">💸</div>
                        <div>تراکنش‌ها</div>
                    </div>
                    <div class="action-btn" onclick="showModal('reports')">
                        <div class="action-icon">📊</div>
                        <div>گزارش‌ها</div>
                    </div>
                    <div class="action-btn" onclick="showModal('settings')">
                        <div class="action-icon">⚙️</div>
                        <div>تنظیمات</div>
                    </div>
                </div>
                
                <div class="recent-list">
                    <h3>آخرین فاکتورها</h3>
                    <div id="recentInvoices">در حال بارگذاری...</div>
                </div>
                
                <div class="recent-list">
                    <h3>آخرین مشتریان</h3>
                    <div id="recentCustomers">در حال بارگذاری...</div>
                </div>
            </div>
        </div>
        
        <script>
            // متغیرهای کاربردی
            let userToken = null;
            let currentUser = null;
            let otpTimer = null;
            let timeLeft = 120;
            let currentPhone = '';
            
            // وقتی صفحه لود شد
            document.addEventListener('DOMContentLoaded', function() {
                console.log('📱 سیستم حسابداری مدرن بارگذاری شد');
                
                // تست اتصال به سرور
                testConnection();
                
                // بررسی اگر کاربر قبلاً وارد شده
                const savedToken = localStorage.getItem('accounting_token');
                if (savedToken) {
                    userToken = savedToken;
                    loadUserProfile();
                }
            });
            
            // تست اتصال به سرور
            async function testConnection() {
                try {
                    const response = await fetch('/api/test');
                    const data = await response.json();
                    console.log('✅ اتصال سرور:', data.message);
                } catch (error) {
                    console.error('❌ خطا در اتصال:', error);
                }
            }
            
            // حرکت بین inputهای OTP
            function moveNext(index) {
                const inputs = document.querySelectorAll('.otp-input');
                const current = inputs[index - 1];
                
                if (current.value.length === 1 && index < 5) {
                    inputs[index].focus();
                }
                
                // بررسی اگر همه پر شدند
                const allFilled = Array.from(inputs).every(input => input.value.length === 1);
                if (allFilled) {
                    verifyOTP();
                }
            }
            
            // ارسال OTP
            async function sendOTP() {
                const phone = document.getElementById('phoneInput').value.trim();
                
                // اعتبارسنجی شماره
                if (!phone || phone.length < 10) {
                    showMessage('لطفاً شماره موبایل معتبر وارد کنید', 'error');
                    return;
                }
                
                currentPhone = phone;
                
                // نمایش loading
                const btn = document.querySelector('#step1 button');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<span class="loading"></span> در حال ارسال...';
                btn.disabled = true;
                
                try {
                    console.log('📤 ارسال درخواست OTP برای:', phone);
                    
                    const response = await fetch('/api/auth/send-otp', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ phone: phone })
                    });
                    
                    const data = await response.json();
                    console.log('📥 پاسخ سرور:', data);
                    
                    if (data.success) {
                        // نمایش مرحله دوم
                        document.getElementById('step1').style.display = 'none';
                        document.getElementById('step2').style.display = 'block';
                        document.getElementById('phoneDisplay').textContent = phone;
                        
                        // شروع تایمر
                        startTimer();
                        
                        // پاک کردن و فوکوس روی اولین input
                        const inputs = document.querySelectorAll('.otp-input');
                        inputs.forEach(input => input.value = '');
                        inputs[0].focus();
                        
                        // نمایش کد برای تست (در محیط واقعی حذف شود)
                        showMessage(`کد تایید: ${data.otp}`, 'success');
                    } else {
                        showMessage(data.error || 'خطا در ارسال کد', 'error');
                    }
                } catch (error) {
                    console.error('❌ خطا در ارسال:', error);
                    showMessage('خطا در ارتباط با سرور', 'error');
                } finally {
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }
            }
            
            // شروع تایمر OTP
            function startTimer() {
                clearInterval(otpTimer);
                timeLeft = 120;
                
                otpTimer = setInterval(() => {
                    timeLeft--;
                    
                    const minutes = Math.floor(timeLeft / 60);
                    const seconds = timeLeft % 60;
                    
                    document.getElementById('timer').textContent = 
                        `${minutes}:${seconds.toString().padStart(2, '0')}`;
                    
                    if (timeLeft <= 0) {
                        clearInterval(otpTimer);
                        showMessage('کد منقضی شده است', 'error');
                    }
                }, 1000);
            }
            
            // بازگشت به مرحله اول
            function backToStep1() {
                document.getElementById('step1').style.display = 'block';
                document.getElementById('step2').style.display = 'none';
                clearInterval(otpTimer);
            }
            
            // تایید OTP و ورود
            async function verifyOTP() {
                const inputs = document.querySelectorAll('.otp-input');
                const otp = Array.from(inputs).map(input => input.value).join('');
                
                if (otp.length !== 5) {
                    showMessage('لطفاً کد ۵ رقمی را کامل وارد کنید', 'error');
                    return;
                }
                
                const btn = document.querySelector('#step2 button');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<span class="loading"></span> در حال بررسی...';
                btn.disabled = true;
                
                try {
                    console.log('🔐 بررسی OTP:', otp);
                    
                    const response = await fetch('/api/auth/verify-otp', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            phone: currentPhone,
                            code: otp
                        })
                    });
                    
                    const data = await response.json();
                    console.log('✅ پاسخ ورود:', data);
                    
                    if (data.success) {
                        // ذخیره توکن
                        userToken = data.token;
                        currentUser = data.user;
                        localStorage.setItem('accounting_token', userToken);
                        
                        // نمایش داشبورد
                        showDashboard();
                        
                        // بارگذاری اطلاعات کاربر
                        loadUserProfile();
                        
                        showMessage('🎉 ورود موفقیت‌آمیز!', 'success');
                    } else {
                        showMessage(data.error || 'کد نامعتبر است', 'error');
                    }
                } catch (error) {
                    console.error('❌ خطا در ورود:', error);
                    showMessage('خطا در ارتباط با سرور', 'error');
                } finally {
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }
            }
            
            // بارگذاری اطلاعات کاربر
            async function loadUserProfile() {
                try {
                    const response = await fetch('/api/user/profile', {
                        headers: {
                            'Authorization': `Bearer ${userToken}`
                        }
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        currentUser = data.user;
                        document.getElementById('welcomeText').textContent = 
                            `سلام ${currentUser.full_name || 'کاربر'} عزیز`;
                        document.getElementById('userPhone').textContent = currentUser.phone;
                        
                        // بارگذاری آمار
                        loadDashboardStats();
                        loadRecentData();
                    }
                } catch (error) {
                    console.error('خطا در بارگذاری پروفایل:', error);
                }
            }
            
            // بارگذاری آمار داشبورد
            async function loadDashboardStats() {
                try {
                    const headers = {
                        'Authorization': `Bearer ${userToken}`
                    };
                    
                    // بارگذاری مشتریان
                    const customersRes = await fetch('/api/customers', { headers });
                    const customersData = await customersRes.json();
                    if (customersData.success) {
                        document.getElementById('customersCount').textContent = customersData.count;
                    }
                    
                    // بارگذاری فاکتورها
                    const invoicesRes = await fetch('/api/invoices', { headers });
                    const invoicesData = await invoicesRes.json();
                    if (invoicesData.success) {
                        document.getElementById('invoicesCount').textContent = invoicesData.count;
                        
                        // محاسبه مجموع
                        const total = invoicesData.invoices.reduce((sum, inv) => sum + inv.total_amount, 0);
                        document.getElementById('balance').textContent = 
                            new Intl.NumberFormat('fa-IR').format(total) + ' تومان';
                    }
                    
                } catch (error) {
                    console.error('خطا در بارگذاری آمار:', error);
                }
            }
            
            // بارگذاری داده‌های اخیر
            async function loadRecentData() {
                // این قسمت را می‌توانید کامل‌تر کنید
                document.getElementById('recentInvoices').innerHTML = 
                    '<p style="text-align: center; opacity: 0.7;">اطلاعات در حال بارگذاری...</p>';
                document.getElementById('recentCustomers').innerHTML = 
                    '<p style="text-align: center; opacity: 0.7;">اطلاعات در حال بارگذاری...</p>';
            }
            
            // نمایش داشبورد
            function showDashboard() {
                document.getElementById('authContainer').style.display = 'none';
                document.getElementById('dashboard').style.display = 'block';
            }
            
            // نمایش پیام
            function showMessage(text, type) {
                const messageDiv = document.getElementById('message');
                messageDiv.textContent = text;
                messageDiv.className = `message ${type}`;
                messageDiv.style.display = 'block';
                
                // مخفی کردن خودکار
                setTimeout(() => {
                    messageDiv.style.display = 'none';
                }, 5000);
            }
            
            // نمایش مودال
            function showModal(type) {
                alert(`مودال ${type} باز خواهد شد`);
                // اینجا می‌توانید مودال‌های مختلف را پیاده‌سازی کنید
            }
            
            // خروج
            function logout() {
                if (confirm('آیا می‌خواهید خارج شوید؟')) {
                    localStorage.removeItem('accounting_token');
                    userToken = null;
                    currentUser = null;
                    
                    document.getElementById('dashboard').style.display = 'none';
                    document.getElementById('authContainer').style.display = 'block';
                    
                    // ریست فرم
                    document.getElementById('phoneInput').value = '';
                    document.querySelectorAll('.otp-input').forEach(input => input.value = '');
                    clearInterval(otpTimer);
                }
            }
        </script>
    </body>
    </html>
    ''')

# ==================== API های احراز هویت ====================
@app.route('/api/auth/send-otp', methods=['POST', 'OPTIONS'])
def send_otp_api():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'داده‌ای دریافت نشد'}), 400
        
        phone = data.get('phone', '').strip()
        if not phone:
            return jsonify({'error': 'شماره تلفن الزامی است'}), 400
        
        print(f"📞 درخواست OTP برای: {phone}")
        
        # تولید کد OTP
        otp_code = generate_otp()
        
        # ذخیره در دیتابیس
        conn = get_db()
        cursor = conn.cursor()
        
        # حذف OTPهای قدیمی
        cursor.execute("DELETE FROM otps WHERE phone = ? AND expires_at < ?", 
                      (phone, datetime.now()))
        
        # ذخیره OTP جدید
        expires_at = datetime.now() + timedelta(minutes=5)
        encrypted_otp = security.encrypt(otp_code)
        cursor.execute(
            "INSERT INTO otps (phone, code, expires_at) VALUES (?, ?, ?)",
            (phone, encrypted_otp, expires_at)
        )
        
        # بررسی یا ایجاد کاربر
        cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
        user = cursor.fetchone()
        
        if not user:
            # ایجاد کاربر جدید
            cursor.execute(
                "INSERT INTO users (phone, full_name) VALUES (?, ?)",
                (phone, f"کاربر {phone}")
            )
            user_id = cursor.lastrowid
            print(f"👤 کاربر جدید ایجاد شد: {user_id}")
        else:
            user_id = user['id']
        
        conn.commit()
        conn.close()
        
        print(f"✅ OTP ارسال شد: {otp_code} برای کاربر: {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'کد تایید ارسال شد',
            'otp': otp_code,  # در محیط واقعی این خط حذف شود
            'user_id': user_id
        }), 200
        
    except Exception as e:
        print(f"❌ خطا در send-otp: {str(e)}")
        return jsonify({'error': f'خطای سرور: {str(e)}'}), 500

@app.route('/api/auth/verify-otp', methods=['POST', 'OPTIONS'])
def verify_otp_api():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'داده‌ای دریافت نشد'}), 400
        
        phone = data.get('phone', '').strip()
        code = data.get('code', '').strip()
        
        if not phone or not code:
            return jsonify({'error': 'شماره تلفن و کد الزامی هستند'}), 400
        
        print(f"🔐 بررسی OTP: {phone} - {code}")
        
        conn = get_db()
        cursor = conn.cursor()
        
        # پیدا کردن OTP معتبر
        cursor.execute(
            "SELECT * FROM otps WHERE phone = ? AND used = 0 AND expires_at > ? ORDER BY id DESC LIMIT 1",
            (phone, datetime.now())
        )
        
        otp_record = cursor.fetchone()
        
        if not otp_record:
            conn.close()
            return jsonify({'error': 'کد یافت نشد یا منقضی شده'}), 400
        
        # بررسی کد
        try:
            stored_code = security.decrypt(otp_record['code'])
            if stored_code != code:
                conn.close()
                return jsonify({'error': 'کد نامعتبر است'}), 400
        except:
            conn.close()
            return jsonify({'error': 'خطا در بررسی کد'}), 400
        
        # علامت‌گذاری کد به عنوان استفاده شده
        cursor.execute("UPDATE otps SET used = 1 WHERE id = ?", (otp_record['id'],))
        
        # پیدا کردن کاربر
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
        
        # تولید توکن
        token = generate_token(user['id'], phone)
        
        conn.commit()
        conn.close()
        
        print(f"✅ ورود موفق: کاربر {user['id']}")
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user['id'],
                'phone': user['phone'],
                'full_name': user['full_name'],
                'business_name': user['business_name'],
                'created_at': user['created_at']
            },
            'message': 'ورود موفقیت‌آمیز'
        }), 200
        
    except Exception as e:
        print(f"❌ خطا در verify-otp: {str(e)}")
        return jsonify({'error': f'خطای سرور: {str(e)}'}), 500

# ==================== API های کاربر ====================
@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_profile(user_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'کاربر پیدا نشد'}), 404
        
        return jsonify({
            'success': True,
            'user': dict(user)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/profile', methods=['PUT'])
@token_required
def update_profile(user_id):
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET 
                full_name = ?,
                email = ?,
                business_name = ?,
                business_type = ?
            WHERE id = ?
        ''', (
            data.get('full_name'),
            data.get('email'),
            data.get('business_name'),
            data.get('business_type'),
            user_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'پروفایل به‌روزرسانی شد'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== API های مشتریان ====================
@app.route('/api/customers', methods=['GET'])
@token_required
def get_customers_api(user_id):
    try:
        conn = get_db()
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
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers', methods=['POST'])
@token_required
def create_customer_api(user_id):
    try:
        data = request.get_json()
        
        # اعتبارسنجی
        if not data.get('name'):
            return jsonify({'error': 'نام مشتری الزامی است'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO customers 
            (user_id, name, phone, email, address, customer_type, notes) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data['name'],
            data.get('phone'),
            data.get('email'),
            data.get('address'),
            data.get('customer_type', 'retail'),
            data.get('notes', '')
        ))
        
        customer_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'مشتری ایجاد شد',
            'customer_id': customer_id
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== API های فاکتور ====================
@app.route('/api/invoices', methods=['GET'])
@token_required
def get_invoices_api(user_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT i.*, c.name as customer_name 
            FROM invoices i 
            LEFT JOIN customers c ON i.customer_id = c.id 
            WHERE i.user_id = ? 
            ORDER BY i.created_at DESC
        ''', (user_id,))
        invoices = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'invoices': invoices,
            'count': len(invoices)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices', methods=['POST'])
@token_required
def create_invoice_api(user_id):
    try:
        data = request.get_json()
        
        # اعتبارسنجی
        if not data.get('items') or len(data['items']) == 0:
            return jsonify({'error': 'حداقل یک آیتم لازم است'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # تولید شماره فاکتور
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{secrets.randbelow(10000):04d}"
        
        # محاسبه مبالغ
        subtotal = sum(item.get('quantity', 0) * item.get('unit_price', 0) for item in data['items'])
        tax_amount = subtotal * (data.get('tax_rate', 0) / 100)
        discount_amount = data.get('discount_amount', 0)
        total_amount = subtotal + tax_amount - discount_amount
        
        # ایجاد QR Code
        qr_data = json.dumps({
            'invoice_number': invoice_number,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total': total_amount,
            'user_id': user_id
        })
        qr_code = generate_qr(qr_data)
        
        # ذخیره فاکتور
        cursor.execute('''
            INSERT INTO invoices 
            (user_id, customer_id, invoice_number, invoice_date, due_date,
             subtotal, tax_amount, discount_amount, total_amount, qr_code) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data.get('customer_id'),
            invoice_number,
            data.get('invoice_date', datetime.now().strftime('%Y-%m-%d')),
            data.get('due_date'),
            subtotal,
            tax_amount,
            discount_amount,
            total_amount,
            qr_code
        ))
        
        invoice_id = cursor.lastrowid
        
        # ذخیره آیتم‌ها
        for item in data['items']:
            total_price = item.get('quantity', 0) * item.get('unit_price', 0)
            cursor.execute('''
                INSERT INTO invoice_items 
                (invoice_id, product_name, quantity, unit_price, total_price) 
                VALUES (?, ?, ?, ?, ?)
            ''', (
                invoice_id,
                item.get('product_name', 'کالا'),
                item.get('quantity', 1),
                item.get('unit_price', 0),
                total_price
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'فاکتور ایجاد شد',
            'invoice_id': invoice_id,
            'invoice_number': invoice_number,
            'total_amount': total_amount,
            'qr_code': qr_code
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== اجرای سرور ====================
if __name__ == '__main__':
    print("=" * 60)
    print("🏦 سیستم حسابداری مدرن")
    print("=" * 60)
    
    # راه‌اندازی دیتابیس
    init_db()
    
    # ایجاد دایرکتوری‌ها
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('backups', exist_ok=True)
    
    print("✅ سیستم آماده است")
    print("🌐 آدرس: http://localhost:5000")
    print("📱 تست: هر شماره تلفنی کار می‌کند")
    print("🔑 کد OTP: ۵ رقمی تولید می‌شود")
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
