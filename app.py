#!/usr/bin/env python3
"""
🏦 سیستم حسابداری مدرن با ارسال واقعی SMS
با استفاده از سرویس Kavenegar
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
import requests  # برای ارسال SMS

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

# ==================== تنظیمات SMS ====================
# API Key کاوه‌نگار (رایگان برای تست - ثبت‌نام کنید)
KAVENEGAR_API_KEY = "YOUR_KAVENEGAR_API_KEY"  # جایگزین کنید با API Key خود
KAVENEGAR_SENDER = "10004346"  # شماره سرویس‌دهنده کاوه‌نگار

# اگر نمی‌خواهید از کاوه‌نگار استفاده کنید، می‌توانید از سرویس‌های دیگر استفاده کنید:
# 1. پیامک (https://peyamak.com)
# 2. مگفا (https://megaweb.ir)
# 3 SMS.ir (https://sms.ir)

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

# ==================== کلاس ارسال SMS ====================
class SMSManager:
    def __init__(self):
        self.api_key = KAVENEGAR_API_KEY
        self.sender = KAVENEGAR_SENDER
        
    def send_sms_kavenegar(self, receptor, message):
        """ارسال SMS با استفاده از Kavenegar"""
        if self.api_key == "YOUR_KAVENEGAR_API_KEY":
            print("⚠️ لطفاً API Key کاوه‌نگار را تنظیم کنید")
            return False
            
        try:
            url = f"https://api.kavenegar.com/v1/{self.api_key}/sms/send.json"
            data = {
                'receptor': receptor,
                'sender': self.sender,
                'message': message
            }
            
            response = requests.post(url, data=data)
            result = response.json()
            
            if result['return']['status'] == 200:
                print(f"✅ SMS ارسال شد به {receptor}")
                return True
            else:
                print(f"❌ خطا در ارسال SMS: {result}")
                return False
                
        except Exception as e:
            print(f"❌ خطا در ارسال SMS: {str(e)}")
            return False
    
    def send_otp_sms(self, phone, otp_code):
        """ارسال کد OTP"""
        message = f"""
        کد تایید حساب‌داری مدرن:
        {otp_code}
        
        این کد ۵ دقیقه اعتبار دارد.
        """
        return self.send_sms_kavenegar(phone, message)
    
    def send_welcome_sms(self, phone, name):
        """ارسال پیام خوش‌آمدگویی"""
        message = f"""
        به سیستم حسابداری مدرن خوش آمدید {name} عزیز!
        
        حساب کاربری شما با موفقیت ایجاد شد.
        برای ورود از شماره موبایل خود استفاده کنید.
        """
        return self.send_sms_kavenegar(phone, message)
    
    def send_invoice_sms(self, phone, invoice_number, amount):
        """اعلام ایجاد فاکتور"""
        message = f"""
        فاکتور جدید:
        شماره: {invoice_number}
        مبلغ: {amount:,} تومان
        
        از طریق پنل کاربری قابل مشاهده است.
        """
        return self.send_sms_kavenegar(phone, message)

# ایجاد شیء مدیریت SMS
sms_manager = SMSManager()

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
            settings TEXT DEFAULT '{}',
            sms_count INTEGER DEFAULT 0
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sms_sent BOOLEAN DEFAULT 0
        )
    ''')
    
    # لاگ SMS ها
    c.execute('''
        CREATE TABLE IF NOT EXISTS sms_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone TEXT NOT NULL,
            message_type TEXT,
            message TEXT,
            status TEXT,
            response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
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
            FOREIGN KEY (ustomer_id) REFERENCES customers(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ دیتابیس ایجاد شد")

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

def log_sms(user_id, phone, message_type, message, status, response):
    """لاگ کردن ارسال SMS"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sms_logs (user_id, phone, message_type, message, status, response)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, phone, message_type, message, status, response))
    conn.commit()
    conn.close()

# ==================== صفحه اصلی ====================
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
            .btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
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
            .sms-info {
                background: rgba(255, 255, 255, 0.1);
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
                font-size: 14px;
            }
            .dashboard {
                display: none;
                padding: 20px;
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
                    <p class="subtitle">کد تایید به پیامک شما ارسال می‌شود</p>
                    
                    <div id="step1">
                        <input type="tel" class="phone-input" id="phoneInput" 
                               placeholder="۰۹۱۲۳۴۵۶۷۸۹" 
                               maxlength="11">
                        <button class="btn" onclick="sendOTP()" id="sendBtn">
                            <span>دریافت کد تایید</span>
                        </button>
                        
                        <div class="sms-info">
                            📱 کد ۵ رقمی به شماره شما ارسال خواهد شد
                            <br>
                            ⏱️ کد به مدت ۵ دقیقه معتبر است
                        </div>
                        
                        <div class="footer">
                            با ادامه، شرایط و حریم خصوصی را می‌پذیرید
                        </div>
                    </div>
                    
                    <div id="step2" style="display: none;">
                        <p>کد تأیید به شماره <span id="phoneDisplay"></span> ارسال شد</p>
                        
                        <div class="sms-info">
                            ✅ پیامک ارسال شد
                            <br>
                            📲 لطفاً کد دریافتی را وارد کنید
                        </div>
                        
                        <div class="otp-inputs">
                            <input type="text" class="otp-input" maxlength="1" oninput="moveNext(1)">
                            <input type="text" class="otp-input" maxlength="1" oninput="moveNext(2)">
                            <input type="text" class="otp-input" maxlength="1" oninput="moveNext(2)">
                            <input type="text" class="otp-input" maxlength="1" oninput="moveNext(4)">
                            <input type="text" class="otp-input" maxlength="1" oninput="moveNext(5)">
                        </div>
                        
                        <div class="timer" id="timer">۰۵:۰۰</div>
                        
                        <button class="btn" onclick="verifyOTP()" id="verifyBtn">
                            <span>تایید و ورود</span>
                        </button>
                        
                        <button class="btn" style="background: rgba(255,255,255,0.1);" 
                                onclick="backToStep1()">
                            تغییر شماره
                        </button>
                        
                        <button class="btn" style="background: rgba(255,193,7,0.2); color: #FFC107;" 
                                onclick="resendOTP()" id="resendBtn" disabled>
                            <span>ارسال مجدد کد</span>
                        </button>
                    </div>
                    
                    <div id="message" class="message"></div>
                </div>
            </div>
            
            <!-- داشبورد -->
            <div class="dashboard" id="dashboard">
                <div style="text-align: center; padding: 40px;">
                    <h1>🎉 ورود موفقیت‌آمیز!</h1>
                    <p>به سیستم حسابداری مدرن خوش آمدید</p>
                    <p id="userInfo"></p>
                    <button class="btn" onclick="logout()" style="margin-top: 30px;">
                        خروج از سیستم
                    </button>
                </div>
            </div>
        </div>
        
        <script>
            let userToken = null;
            let currentUser = null;
            let otpTimer = null;
            let timeLeft = 300; // 5 دقیقه
            let currentPhone = '';
            let canResend = false;
            let resendTimer = 60; // 1 دقیقه برای ارسال مجدد
            
            // وقتی صفحه لود شد
            document.addEventListener('DOMContentLoaded', function() {
                console.log('📱 سیستم حسابداری بارگذاری شد');
                
                // بررسی اگر کاربر قبلاً وارد شده
                const savedToken = localStorage.getItem('accounting_token');
                if (savedToken) {
                    userToken = savedToken;
                    showDashboard();
                    loadUserInfo();
                }
            });
            
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
                    document.getElementById('verifyBtn').focus();
                }
            }
            
            // ارسال OTP
            async function sendOTP() {
                const phone = document.getElementById('phoneInput').value.trim();
                
                // اعتبارسنجی شماره
                if (!phone || phone.length < 10 || !phone.startsWith('09')) {
                    showMessage('لطفاً شماره موبایل معتبر وارد کنید (شروع با ۰۹)', 'error');
                    return;
                }
                
                currentPhone = phone;
                
                // غیرفعال کردن دکمه و نمایش loading
                const btn = document.getElementById('sendBtn');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<span class="loading"></span> در حال ارسال پیامک...';
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
                        
                        // شروع تایمرها
                        startOTPTimer();
                        startResendTimer();
                        
                        // پاک کردن و فوکوس روی اولین input
                        const inputs = document.querySelectorAll('.otp-input');
                        inputs.forEach(input => input.value = '');
                        inputs[0].focus();
                        
                        showMessage('✅ پیامک حاوی کد تایید ارسال شد', 'success');
                        
                        // نمایش کد در کنسول برای تست (در صورت نیاز)
                        if (data.debug_otp) {
                            console.log('🔐 کد OTP (برای تست):', data.debug_otp);
                        }
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
            
            // شروع تایمر OTP (5 دقیقه)
            function startOTPTimer() {
                clearInterval(otpTimer);
                timeLeft = 300;
                
                otpTimer = setInterval(() => {
                    timeLeft--;
                    
                    const minutes = Math.floor(timeLeft / 60);
                    const seconds = timeLeft % 60;
                    
                    document.getElementById('timer').textContent = 
                        `${minutes.toString().padStart(2, '۰')}:${seconds.toString().padStart(2, '۰')}`;
                    
                    if (timeLeft <= 0) {
                        clearInterval(otpTimer);
                        showMessage('⏰ کد منقضی شده است. لطفاً مجدداً درخواست کد دهید', 'error');
                        document.getElementById('verifyBtn').disabled = true;
                    }
                }, 1000);
            }
            
            // تایمر ارسال مجدد (1 دقیقه)
            function startResendTimer() {
                canResend = false;
                resendTimer = 60;
                const resendBtn = document.getElementById('resendBtn');
                resendBtn.disabled = true;
                
                const resendInterval = setInterval(() => {
                    resendTimer--;
                    
                    if (resendTimer <= 0) {
                        clearInterval(resendInterval);
                        canResend = true;
                        resendBtn.disabled = false;
                        resendBtn.innerHTML = '<span>ارسال مجدد کد</span>';
                    } else {
                        resendBtn.innerHTML = `<span>ارسال مجدد (${resendTimer})</span>`;
                    }
                }, 1000);
            }
            
            // ارسال مجدد کد
            async function resendOTP() {
                if (!canResend) return;
                
                const btn = document.getElementById('resendBtn');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<span class="loading"></span> در حال ارسال...';
                btn.disabled = true;
                
                try {
                    const response = await fetch('/api/auth/resend-otp', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ phone: currentPhone })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        // ریست تایمرها
                        clearInterval(otpTimer);
                        startOTPTimer();
                        startResendTimer();
                        
                        // پاک کردن inputها
                        document.querySelectorAll('.otp-input').forEach(input => input.value = '');
                        document.querySelector('.otp-input').focus();
                        
                        showMessage('✅ کد جدید ارسال شد', 'success');
                        
                        // نمایش کد در کنسول برای تست
                        if (data.debug_otp) {
                            console.log('🔐 کد OTP جدید (برای تست):', data.debug_otp);
                        }
                    } else {
                        showMessage(data.error || 'خطا در ارسال مجدد', 'error');
                    }
                } catch (error) {
                    showMessage('خطا در ارتباط با سرور', 'error');
                } finally {
                    btn.innerHTML = originalText;
                    btn.disabled = !canResend;
                }
            }
            
            // بازگشت به مرحله اول
            function backToStep1() {
                document.getElementById('step1').style.display = 'block';
                document.getElementById('step2').style.display = 'none';
                clearInterval(otpTimer);
                document.getElementById('phoneInput').value = currentPhone;
                document.getElementById('phoneInput').focus();
            }
            
            // تایید OTP
            async function verifyOTP() {
                const inputs = document.querySelectorAll('.otp-input');
                const otp = Array.from(inputs).map(input => input.value).join('');
                
                if (otp.length !== 5) {
                    showMessage('لطفاً کد ۵ رقمی را کامل وارد کنید', 'error');
                    return;
                }
                
                const btn = document.getElementById('verifyBtn');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<span class="loading"></span> در حال بررسی...';
                btn.disabled = true;
                
                try {
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
                        loadUserInfo();
                        
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
            async function loadUserInfo() {
                try {
                    const response = await fetch('/api/user/profile', {
                        headers: {
                            'Authorization': `Bearer ${userToken}`
                        }
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        currentUser = data.user;
                        document.getElementById('userInfo').innerHTML = `
                            <strong>${currentUser.full_name || 'کاربر'}</strong><br>
                            ${currentUser.phone}<br>
                            ${currentUser.business_name ? 'کسب‌وکار: ' + currentUser.business_name : ''}
                        `;
                    }
                } catch (error) {
                    console.error('خطا در بارگذاری اطلاعات:', error);
                }
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
                
                setTimeout(() => {
                    messageDiv.style.display = 'none';
                }, 5000);
            }
            
            // خروج
            function logout() {
                if (confirm('آیا می‌خواهید از حساب کاربری خارج شوید؟')) {
                    localStorage.removeItem('accounting_token');
                    userToken = null;
                    currentUser = null;
                    
                    document.getElementById('dashboard').style.display = 'none';
                    document.getElementById('authContainer').style.display = 'block';
                    
                    // ریست فرم
                    document.getElementById('phoneInput').value = '';
                    document.querySelectorAll('.otp-input').forEach(input => input.value = '');
                    clearInterval(otpTimer);
                    
                    showMessage('✅ با موفقیت خارج شدید', 'success');
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
            "INSERT INTO otps (phone, code, expires_at, sms_sent) VALUES (?, ?, ?, ?)",
            (phone, encrypted_otp, expires_at, 1)
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
        
        # ==================== ارسال واقعی SMS ====================
        sms_sent = False
        sms_response = "در حال تست - SMS ارسال نشد"
        
        try:
            # ارسال SMS با کاوه‌نگار
            sms_sent = sms_manager.send_otp_sms(phone, otp_code)
            sms_response = "ارسال شد" if sms_sent else "خطا در ارسال"
            
            # لاگ SMS
            log_sms(user_id, phone, 'otp', otp_code, 
                   'success' if sms_sent else 'failed', 
                   sms_response)
            
        except Exception as sms_error:
            print(f"❌ خطا در ارسال SMS: {sms_error}")
            sms_response = str(sms_error)
            log_sms(user_id, phone, 'otp', otp_code, 'failed', sms_response)
        
        print(f"✅ OTP تولید شد: {otp_code}")
        print(f"📱 وضعیت SMS: {sms_response}")
        
        response_data = {
            'success': True,
            'message': 'کد تایید ارسال شد' if sms_sent else 'کد تولید شد اما پیامک ارسال نشد',
            'user_id': user_id,
            'sms_sent': sms_sent
        }
        
        # در محیط توسعه، کد را هم برمی‌گردانیم
        if not sms_sent:
            response_data['debug_otp'] = otp_code
            response_data['debug_message'] = 'لطفاً API Key کاوه‌نگار را تنظیم کنید'
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"❌ خطا در send-otp: {str(e)}")
        return jsonify({'error': f'خطای سرور: {str(e)}'}), 500

@app.route('/api/auth/resend-otp', methods=['POST', 'OPTIONS'])
def resend_otp_api():
    """ارسال مجدد کد OTP"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        
        if not phone:
            return jsonify({'error': 'شماره تلفن الزامی است'}), 400
        
        print(f"🔄 درخواست ارسال مجدد OTP برای: {phone}")
        
        # تولید کد جدید
        new_otp = generate_otp()
        
        conn = get_db()
        cursor = conn.cursor()
        
        # آپدیت آخرین OTP
        expires_at = datetime.now() + timedelta(minutes=5)
        encrypted_otp = security.encrypt(new_otp)
        
        cursor.execute('''
            UPDATE otps 
            SET code = ?, expires_at = ?, created_at = ?, used = 0, sms_sent = 1
            WHERE phone = ? AND expires_at > ?
            ORDER BY id DESC LIMIT 1
        ''', (encrypted_otp, expires_at, datetime.now(), phone, datetime.now()))
        
        if cursor.rowcount == 0:
            # اگر OTP فعالی نبود، ایجاد جدید
            cursor.execute(
                "INSERT INTO otps (phone, code, expires_at, sms_sent) VALUES (?, ?, ?, ?)",
                (phone, encrypted_otp, expires_at, 1)
            )
        
        conn.commit()
        
        # پیدا کردن user_id
        cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
        user = cursor.fetchone()
        user_id = user['id'] if user else None
        
        conn.close()
        
        # ارسال SMS
        sms_sent = sms_manager.send_otp_sms(phone, new_otp)
        
        if user_id:
            log_sms(user_id, phone, 'otp_resend', new_otp, 
                   'success' if sms_sent else 'failed',
                   'ارسال مجدد')
        
        response_data = {
            'success': True,
            'message': 'کد جدید ارسال شد' if sms_sent else 'کد تولید شد اما پیامک ارسال نشد',
            'sms_sent': sms_sent
        }
        
        if not sms_sent:
            response_data['debug_otp'] = new_otp
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/verify-otp', methods=['POST', 'OPTIONS'])
def verify_otp_api():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        data = request.get_json()
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
        
        # آپدیت زمان آخرین ورود و افزایش شمارش SMS
        cursor.execute('''
            UPDATE users 
            SET last_login = ?, sms_count = sms_count + 1 
            WHERE id = ?
        ''', (datetime.now(), user['id']))
        
        # تولید توکن
        token = generate_token(user['id'], phone)
        
        conn.commit()
        conn.close()
        
        print(f"✅ ورود موفق: کاربر {user['id']}")
        
        # ارسال پیام خوش‌آمدگویی
        try:
            sms_manager.send_welcome_sms(phone, user['full_name'] or 'کاربر')
        except:
            pass
        
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

# ==================== اجرای سرور ====================
if __name__ == '__main__':
    print("=" * 60)
    print("🏦 سیستم حسابداری مدرن با ارسال واقعی SMS")
    print("=" * 60)
    
    # راه‌اندازی دیتابیس
    init_db()
    
    # بررسی تنظیمات SMS
    if KAVENEGAR_API_KEY == "YOUR_KAVENEGAR_API_KEY":
        print("⚠️  هشدار: API Key کاوه‌نگار تنظیم نشده است!")
        print("📝 برای ارسال واقعی SMS:")
        print("1. به سایت kavenegar.com بروید")
        print("2. ثبت‌نام کنید و API Key دریافت کنید")
        print("3. در کد، KAVENEGAR_API_KEY را جایگزین کنید")
        print("🔧 فعلاً کد OTP در کنسول نمایش داده می‌شود")
    else:
        print("✅ SMS فعال است - کدها به پیامک ارسال می‌شوند")
    
    print("✅ سیستم آماده است")
    print("🌐 آدرس: http://localhost:5000")
    print("📱 تست: هر شماره تلفنی کار می‌کند")
    print("⏱️  کد OTP: 5 دقیقه اعتبار")
    print("🔄 ارسال مجدد: پس از 1 دقیقه")
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
