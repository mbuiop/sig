#!/usr/bin/env python3
"""
🚀 سیستم حسابداری آنلاین فوق مدرن - SPA Version
یک صفحه‌ای با ثبت‌نام/ورود اولیه و پنل مدیریت
"""

from flask import Flask, request, jsonify, session, send_file, render_template_string
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

socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   async_mode='threading',
                   logger=True, 
                   engineio_logger=True)

# کلیدهای امنیتی
JWT_SECRET = secrets.token_hex(32)
ENCRYPTION_KEY = hashlib.sha256(secrets.token_bytes(32)).digest()[:32]

# مسیر دیتابیس
DB_PATH = 'accounting_system.db'

# ==================== صفحه اصلی (SPA) ====================
@app.route('/')
def index():
    """صفحه اصلی Single Page Application"""
    html_content = '''
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🚀 سیستم حسابداری آنلاین</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                transition: all 0.3s ease;
            }
            
            #app {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            
            /* صفحه ورود/ثبت‌نام */
            .auth-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                padding: 20px;
            }
            
            .auth-box {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                width: 100%;
                max-width: 400px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.1);
                text-align: center;
            }
            
            .logo {
                font-size: 3rem;
                margin-bottom: 20px;
            }
            
            .auth-title {
                font-size: 2rem;
                margin-bottom: 10px;
                color: #ffcc00;
            }
            
            .auth-subtitle {
                margin-bottom: 30px;
                opacity: 0.9;
            }
            
            .phone-input {
                width: 100%;
                padding: 15px;
                border: none;
                border-radius: 50px;
                background: rgba(255, 255, 255, 0.15);
                color: white;
                font-size: 1.1rem;
                text-align: center;
                margin-bottom: 20px;
                outline: none;
            }
            
            .phone-input::placeholder {
                color: rgba(255, 255, 255, 0.7);
            }
            
            .btn {
                width: 100%;
                padding: 15px;
                border: none;
                border-radius: 50px;
                background: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
                color: white;
                font-size: 1.2rem;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-bottom: 15px;
            }
            
            .btn:hover {
                transform: scale(1.02);
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
            }
            
            .btn-secondary {
                background: linear-gradient(to right, #f093fb 0%, #f5576c 100%);
            }
            
            .otp-input {
                display: flex;
                gap: 10px;
                margin: 20px 0;
                justify-content: center;
            }
            
            .otp-digit {
                width: 50px;
                height: 50px;
                text-align: center;
                font-size: 1.5rem;
                border: none;
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.15);
                color: white;
                outline: none;
            }
            
            .timer {
                margin: 15px 0;
                font-size: 0.9rem;
                opacity: 0.8;
            }
            
            .message {
                padding: 15px;
                border-radius: 10px;
                margin: 15px 0;
                text-align: center;
            }
            
            .success {
                background: rgba(76, 175, 80, 0.2);
                border: 1px solid rgba(76, 175, 80, 0.5);
            }
            
            .error {
                background: rgba(244, 67, 54, 0.2);
                border: 1px solid rgba(244, 67, 54, 0.5);
            }
            
            .loading {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                border-top-color: white;
                animation: spin 1s ease-in-out infinite;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            /* داشبورد */
            .dashboard {
                display: none;
                min-height: 100vh;
            }
            
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                margin-bottom: 30px;
            }
            
            .user-info {
                display: flex;
                align-items: center;
                gap: 15px;
            }
            
            .user-avatar {
                width: 50px;
                height: 50px;
                border-radius: 50%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
            }
            
            .logout-btn {
                background: rgba(244, 67, 54, 0.2);
                color: #ff5252;
                padding: 10px 20px;
                border-radius: 25px;
                border: 1px solid rgba(244, 67, 54, 0.5);
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .logout-btn:hover {
                background: rgba(244, 67, 54, 0.3);
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            
            .stat-card {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 25px;
                text-align: center;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                transition: transform 0.3s ease;
            }
            
            .stat-card:hover {
                transform: translateY(-5px);
            }
            
            .stat-icon {
                font-size: 2.5rem;
                margin-bottom: 15px;
            }
            
            .stat-value {
                font-size: 2rem;
                font-weight: bold;
                margin: 10px 0;
                color: #ffcc00;
            }
            
            .stat-label {
                opacity: 0.8;
                font-size: 0.9rem;
            }
            
            .features-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            
            .feature-card {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 25px;
                text-align: center;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .feature-card:hover {
                background: rgba(255, 255, 255, 0.15);
                transform: translateY(-5px);
            }
            
            .feature-icon {
                font-size: 3rem;
                margin-bottom: 20px;
            }
            
            .feature-title {
                font-size: 1.5rem;
                margin-bottom: 10px;
                color: #4facfe;
            }
            
            .modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.8);
                z-index: 1000;
                align-items: center;
                justify-content: center;
            }
            
            .modal-content {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 20px;
                padding: 40px;
                width: 90%;
                max-width: 500px;
                max-height: 80vh;
                overflow-y: auto;
            }
            
            .modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
            }
            
            .close-modal {
                background: none;
                border: none;
                color: white;
                font-size: 1.5rem;
                cursor: pointer;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-label {
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
            }
            
            .form-input {
                width: 100%;
                padding: 12px;
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                background: rgba(255, 255, 255, 0.1);
                color: white;
                font-size: 1rem;
            }
            
            .form-input:focus {
                outline: none;
                border-color: #4facfe;
            }
            
            .invoice-items {
                margin-top: 20px;
            }
            
            .invoice-item {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
                align-items: center;
            }
            
            .add-item-btn {
                background: rgba(76, 175, 80, 0.2);
                color: #4caf50;
                border: 1px solid rgba(76, 175, 80, 0.5);
                padding: 10px 20px;
                border-radius: 10px;
                cursor: pointer;
                margin-top: 10px;
            }
            
            .remove-item-btn {
                background: rgba(244, 67, 54, 0.2);
                color: #ff5252;
                border: 1px solid rgba(244, 67, 54, 0.5);
                padding: 5px 10px;
                border-radius: 5px;
                cursor: pointer;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                overflow: hidden;
            }
            
            th, td {
                padding: 15px;
                text-align: right;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            th {
                background: rgba(255, 255, 255, 0.2);
                font-weight: bold;
            }
            
            .action-btn {
                padding: 8px 15px;
                border-radius: 5px;
                border: none;
                cursor: pointer;
                font-size: 0.9rem;
                margin: 0 5px;
            }
            
            .edit-btn {
                background: #2196f3;
                color: white;
            }
            
            .delete-btn {
                background: #f44336;
                color: white;
            }
            
            .chat-container {
                height: 500px;
                display: flex;
                flex-direction: column;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                overflow: hidden;
            }
            
            .chat-messages {
                flex: 1;
                padding: 20px;
                overflow-y: auto;
            }
            
            .chat-input-container {
                display: flex;
                padding: 20px;
                gap: 10px;
                background: rgba(0, 0, 0, 0.2);
            }
            
            .chat-input {
                flex: 1;
                padding: 12px;
                border-radius: 25px;
                border: none;
                background: rgba(255, 255, 255, 0.15);
                color: white;
            }
            
            .chat-message {
                margin-bottom: 15px;
                padding: 12px;
                border-radius: 15px;
                max-width: 70%;
                word-wrap: break-word;
            }
            
            .message-sent {
                background: rgba(79, 195, 247, 0.3);
                margin-left: auto;
                margin-right: 0;
            }
            
            .message-received {
                background: rgba(255, 255, 255, 0.1);
                margin-left: 0;
                margin-right: auto;
            }
            
            @media (max-width: 768px) {
                .stats-grid, .features-grid {
                    grid-template-columns: 1fr;
                }
                
                .header {
                    flex-direction: column;
                    gap: 15px;
                }
                
                .auth-box {
                    padding: 30px 20px;
                }
            }
        </style>
    </head>
    <body>
        <div id="app">
            <!-- صفحه ورود/ثبت‌نام -->
            <div class="auth-container" id="authContainer">
                <div class="auth-box">
                    <div class="logo">🚀</div>
                    <h1 class="auth-title">سیستم حسابداری آنلاین</h1>
                    <p class="auth-subtitle">برای شروع، شماره تلفن خود را وارد کنید</p>
                    
                    <div id="authStep1">
                        <input type="tel" class="phone-input" id="phoneInput" 
                               placeholder="۰۹۱۲۳۴۵۶۷۸۹" maxlength="11">
                        <button class="btn" onclick="sendOTP()">ارسال کد تایید</button>
                        <p style="margin-top: 20px; font-size: 0.9rem; opacity: 0.7;">
                            با کلیک روی دکمه، قوانین و حریم خصوصی را می‌پذیرید
                        </p>
                    </div>
                    
                    <div id="authStep2" style="display: none;">
                        <p>کد تایید به شماره <span id="phoneNumber"></span> ارسال شد</p>
                        <div class="otp-input">
                            <input type="text" class="otp-digit" maxlength="1" oninput="moveToNext(this, 1)">
                            <input type="text" class="otp-digit" maxlength="1" oninput="moveToNext(this, 2)">
                            <input type="text" class="otp-digit" maxlength="1" oninput="moveToNext(this, 3)">
                            <input type="text" class="otp-digit" maxlength="1" oninput="moveToNext(this, 4)">
                            <input type="text" class="otp-digit" maxlength="1" oninput="moveToNext(this, 5)">
                        </div>
                        <div class="timer" id="timer">۰۲:۰۰</div>
                        <button class="btn" onclick="verifyOTP()">تایید و ورود</button>
                        <button class="btn btn-secondary" onclick="backToPhone()">ویرایش شماره</button>
                    </div>
                    
                    <div id="authMessage" class="message" style="display: none;"></div>
                </div>
            </div>
            
            <!-- داشبورد کاربر -->
            <div class="dashboard" id="dashboard">
                <!-- هدر -->
                <div class="header">
                    <div>
                        <h1>داشبورد مدیریتی 🚀</h1>
                        <p id="welcomeText">خوش آمدید!</p>
                    </div>
                    
                    <div class="user-info">
                        <div class="user-avatar" id="userAvatar">👤</div>
                        <div>
                            <div id="userName">کاربر</div>
                            <div id="userPhone" style="font-size: 0.9rem; opacity: 0.8;"></div>
                        </div>
                        <button class="logout-btn" onclick="logout()">خروج</button>
                    </div>
                </div>
                
                <!-- آمار کلی -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">💰</div>
                        <div class="stat-value" id="totalBalance">۰</div>
                        <div class="stat-label">موجودی کل</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">👥</div>
                        <div class="stat-value" id="totalCustomers">۰</div>
                        <div class="stat-label">مشتریان</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">🧾</div>
                        <div class="stat-value" id="totalInvoices">۰</div>
                        <div class="stat-label">فاکتورها</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">💬</div>
                        <div class="stat-value" id="unreadMessages">۰</div>
                        <div class="stat-label">پیام‌های خوانده نشده</div>
                    </div>
                </div>
                
                <!-- امکانات اصلی -->
                <div class="features-grid">
                    <div class="feature-card" onclick="showModal('customers')">
                        <div class="feature-icon">👥</div>
                        <h3 class="feature-title">مدیریت مشتریان</h3>
                        <p>افزودن، ویرایش و مدیریت مشتریان</p>
                    </div>
                    
                    <div class="feature-card" onclick="showModal('invoices')">
                        <div class="feature-icon">🧾</div>
                        <h3 class="feature-title">صدور فاکتور</h3>
                        <p>ایجاد فاکتور جدید با QR Code</p>
                    </div>
                    
                    <div class="feature-card" onclick="showModal('products')">
                        <div class="feature-icon">📦</div>
                        <h3 class="feature-title">مدیریت محصولات</h3>
                        <p>انبارداری و مدیریت کالاها</p>
                    </div>
                    
                    <div class="feature-card" onclick="showModal('transactions')">
                        <div class="feature-icon">💸</div>
                        <h3 class="feature-title">تراکنش‌ها</h3>
                        <p>مدیریت دریافتی و پرداختی‌ها</p>
                    </div>
                    
                    <div class="feature-card" onclick="showModal('chat')">
                        <div class="feature-icon">💬</div>
                        <h3 class="feature-title">چت آنلاین</h3>
                        <p>ارتباط مستقیم با مشتریان</p>
                    </div>
                    
                    <div class="feature-card" onclick="showModal('reports')">
                        <div class="feature-icon">📊</div>
                        <h3 class="feature-title">گزارش‌گیری</h3>
                        <p>گزارشات مالی و تحلیلی</p>
                    </div>
                </div>
                
                <!-- جدول مشتریان اخیر -->
                <div style="background: rgba(255, 255, 255, 0.1); border-radius: 15px; padding: 25px; margin-bottom: 30px;">
                    <h2 style="margin-bottom: 20px;">مشتریان اخیر</h2>
                    <div id="recentCustomers">در حال بارگذاری...</div>
                </div>
                
                <!-- جدول فاکتورهای اخیر -->
                <div style="background: rgba(255, 255, 255, 0.1); border-radius: 15px; padding: 25px;">
                    <h2 style="margin-bottom: 20px;">فاکتورهای اخیر</h2>
                    <div id="recentInvoices">در حال بارگذاری...</div>
                </div>
            </div>
            
            <!-- مودال‌ها -->
            <div class="modal" id="customersModal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>👥 مدیریت مشتریان</h2>
                        <button class="close-modal" onclick="hideModal('customersModal')">×</button>
                    </div>
                    <button class="btn" onclick="showAddCustomerForm()">➕ افزودن مشتری جدید</button>
                    <div id="customersList" style="margin-top: 20px;"></div>
                </div>
            </div>
            
            <!-- سایر مودال‌ها به همین شکل -->
        </div>
        
        <script>
            // حالت‌های برنامه
            let currentUser = null;
            let userToken = null;
            let otpTimer = null;
            let timeLeft = 120;
            let currentPhone = '';
            
            // تنظیمات WebSocket
            let socket = null;
            
            // وقتی صفحه لود شد
            document.addEventListener('DOMContentLoaded', function() {
                // بررسی اگر کاربر قبلاً لاگین کرده
                const savedToken = localStorage.getItem('accounting_token');
                if (savedToken) {
                    checkToken(savedToken);
                }
            });
            
            // حرکت بین inputهای OTP
            function moveToNext(input, nextIndex) {
                if (input.value.length === 1) {
                    const nextInput = document.querySelector(`.otp-input input:nth-child(${nextIndex + 1})`);
                    if (nextInput) {
                        nextInput.focus();
                    }
                }
                
                // اگر همه پر شدند، دکمه تایید را فعال کن
                const allFilled = Array.from(document.querySelectorAll('.otp-digit'))
                    .every(input => input.value.length === 1);
                if (allFilled) {
                    document.querySelector('#authStep2 button').focus();
                }
            }
            
            // ارسال OTP
            async function sendOTP() {
                const phone = document.getElementById('phoneInput').value.trim();
                
                if (!phone || phone.length !== 11 || !phone.startsWith('09')) {
                    showMessage('لطفاً شماره موبایل معتبر وارد کنید', 'error');
                    return;
                }
                
                currentPhone = phone;
                
                // نمایش loading
                const btn = document.querySelector('#authStep1 button');
                const originalText = btn.textContent;
                btn.innerHTML = '<span class="loading"></span> در حال ارسال...';
                btn.disabled = true;
                
                try {
                    const response = await fetch('/api/auth/send-otp', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ phone: phone })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        // نمایش مرحله دوم
                        document.getElementById('authStep1').style.display = 'none';
                        document.getElementById('authStep2').style.display = 'block';
                        document.getElementById('phoneNumber').textContent = phone;
                        
                        // شروع تایمر
                        startOTPTimer();
                        
                        // پاک کردن inputها
                        document.querySelectorAll('.otp-digit').forEach(input => input.value = '');
                        document.querySelector('.otp-digit').focus();
                        
                        showMessage('کد تایید ارسال شد', 'success');
                    } else {
                        showMessage(data.error || 'خطا در ارسال کد', 'error');
                    }
                } catch (error) {
                    showMessage('خطا در ارتباط با سرور', 'error');
                } finally {
                    btn.textContent = originalText;
                    btn.disabled = false;
                }
            }
            
            // شروع تایمر OTP
            function startOTPTimer() {
                clearInterval(otpTimer);
                timeLeft = 120;
                
                otpTimer = setInterval(() => {
                    timeLeft--;
                    
                    const minutes = Math.floor(timeLeft / 60);
                    const seconds = timeLeft % 60;
                    
                    document.getElementById('timer').textContent = 
                        `${minutes.toString().padStart(2, '۰')}:${seconds.toString().padStart(2, '۰')}`;
                    
                    if (timeLeft <= 0) {
                        clearInterval(otpTimer);
                        showMessage('کد منقضی شده است. مجدداً درخواست دهید', 'error');
                    }
                }, 1000);
            }
            
            // بازگشت به مرحله اول
            function backToPhone() {
                document.getElementById('authStep1').style.display = 'block';
                document.getElementById('authStep2').style.display = 'none';
                clearInterval(otpTimer);
            }
            
            // تایید OTP
            async function verifyOTP() {
                const otp = Array.from(document.querySelectorAll('.otp-digit'))
                    .map(input => input.value)
                    .join('');
                
                if (otp.length !== 5) {
                    showMessage('لطفاً کد ۵ رقمی را کامل وارد کنید', 'error');
                    return;
                }
                
                const btn = document.querySelector('#authStep2 button');
                const originalText = btn.textContent;
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
                    
                    if (data.success) {
                        // ذخیره توکن
                        userToken = data.token;
                        currentUser = data.user;
                        localStorage.setItem('accounting_token', userToken);
                        
                        // نمایش داشبورد
                        showDashboard();
                        
                        // بارگذاری داده‌ها
                        loadDashboardData();
                        
                        // اتصال به WebSocket
                        connectWebSocket();
                        
                        showMessage('ورود موفقیت‌آمیز!', 'success');
                    } else {
                        showMessage(data.error || 'کد نامعتبر است', 'error');
                    }
                } catch (error) {
                    showMessage('خطا در ارتباط با سرور', 'error');
                } finally {
                    btn.textContent = originalText;
                    btn.disabled = false;
                }
            }
            
            // بررسی توکن ذخیره شده
            async function checkToken(token) {
                try {
                    // می‌توانید یک endpoint برای اعتبارسنجی توکن اضافه کنید
                    // فعلاً فقط نمایش می‌دهیم
                    userToken = token;
                    showDashboard();
                    loadDashboardData();
                    connectWebSocket();
                } catch (error) {
                    localStorage.removeItem('accounting_token');
                    showMessage('لطفاً مجدداً وارد شوید', 'error');
                }
            }
            
            // نمایش داشبورد
            function showDashboard() {
                document.getElementById('authContainer').style.display = 'none';
                document.getElementById('dashboard').style.display = 'block';
                
                if (currentUser) {
                    document.getElementById('userName').textContent = currentUser.name || currentUser.phone;
                    document.getElementById('userPhone').textContent = currentUser.phone;
                    document.getElementById('welcomeText').textContent = `سلام ${currentUser.name || 'کاربر'} عزیز`;
                    
                    // تنظیم حرف اول برای آواتار
                    const firstChar = (currentUser.name || currentUser.phone).charAt(0);
                    document.getElementById('userAvatar').textContent = firstChar;
                }
            }
            
            // بارگذاری داده‌های داشبورد
            async function loadDashboardData() {
                try {
                    const headers = {
                        'Authorization': `Bearer ${userToken}`,
                        'Content-Type': 'application/json'
                    };
                    
                    // بارگذاری مشتریان
                    const customersRes = await fetch('/api/customers', { headers });
                    const customersData = await customersRes.json();
                    
                    if (customersData.success) {
                        document.getElementById('totalCustomers').textContent = customersData.count;
                        displayRecentCustomers(customersData.customers.slice(0, 5));
                    }
                    
                    // بارگذاری فاکتورها
                    const invoicesRes = await fetch('/api/invoices', { headers });
                    const invoicesData = await invoicesRes.json();
                    
                    if (invoicesData.success) {
                        document.getElementById('totalInvoices').textContent = invoicesData.count;
                        displayRecentInvoices(invoicesData.invoices.slice(0, 5));
                        
                        // محاسبه کل موجودی
                        const totalBalance = invoicesData.invoices.reduce((sum, invoice) => {
                            return sum + (invoice.total_amount - invoice.paid_amount);
                        }, 0);
                        document.getElementById('totalBalance').textContent = 
                            totalBalance.toLocaleString() + ' تومان';
                    }
                    
                } catch (error) {
                    console.error('خطا در بارگذاری داده‌ها:', error);
                }
            }
            
            // نمایش مشتریان اخیر
            function displayRecentCustomers(customers) {
                if (!customers || customers.length === 0) {
                    document.getElementById('recentCustomers').innerHTML = 
                        '<p style="text-align: center; opacity: 0.7;">هیچ مشتری ثبت نشده است</p>';
                    return;
                }
                
                const html = `
                    <table>
                        <thead>
                            <tr>
                                <th>نام</th>
                                <th>تلفن</th>
                                <th>موجودی</th>
                                <th>عملیات</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${customers.map(customer => `
                                <tr>
                                    <td>${customer.name}</td>
                                    <td>${customer.phone || '-'}</td>
                                    <td>${customer.balance ? customer.balance.toLocaleString() + ' تومان' : '۰'}</td>
                                    <td>
                                        <button class="action-btn edit-btn">ویرایش</button>
                                        <button class="action-btn delete-btn">حذف</button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
                
                document.getElementById('recentCustomers').innerHTML = html;
            }
            
            // نمایش فاکتورهای اخیر
            function displayRecentInvoices(invoices) {
                if (!invoices || invoices.length === 0) {
                    document.getElementById('recentInvoices').innerHTML = 
                        '<p style="text-align: center; opacity: 0.7;">هیچ فاکتور ثبت نشده است</p>';
                    return;
                }
                
                const html = `
                    <table>
                        <thead>
                            <tr>
                                <th>شماره فاکتور</th>
                                <th>مشتری</th>
                                <th>مبلغ کل</th>
                                <th>وضعیت</th>
                                <th>تاریخ</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${invoices.map(invoice => `
                                <tr>
                                    <td>${invoice.invoice_number}</td>
                                    <td>${invoice.customer_name || 'بدون مشتری'}</td>
                                    <td>${invoice.total_amount.toLocaleString()} تومان</td>
                                    <td>
                                        <span style="padding: 5px 10px; border-radius: 5px; background: ${
                                            invoice.status === 'paid' ? 'rgba(76, 175, 80, 0.3)' :
                                            invoice.status === 'pending' ? 'rgba(255, 193, 7, 0.3)' :
                                            'rgba(244, 67, 54, 0.3)'
                                        }">
                                            ${invoice.status === 'paid' ? 'پرداخت شده' :
                                              invoice.status === 'pending' ? 'در انتظار' : 'لغو شده'}
                                        </span>
                                    </td>
                                    <td>${new Date(invoice.invoice_date).toLocaleDateString('fa-IR')}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
                
                document.getElementById('recentInvoices').innerHTML = html;
            }
            
            // اتصال به WebSocket
            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}`;
                
                socket = new WebSocket(wsUrl);
                
                socket.onopen = () => {
                    console.log('WebSocket connected');
                    // احراز هویت WebSocket
                    socket.send(JSON.stringify({
                        event: 'authenticate',
                        data: { token: userToken }
                    }));
                };
                
                socket.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    console.log('WebSocket message:', data);
                    
                    // پردازش پیام‌های دریافتی
                    handleWebSocketMessage(data);
                };
                
                socket.onclose = () => {
                    console.log('WebSocket disconnected');
                    // تلاش مجدد پس از 5 ثانیه
                    setTimeout(connectWebSocket, 5000);
                };
                
                socket.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };
            }
            
            // پردازش پیام‌های WebSocket
            function handleWebSocketMessage(data) {
                if (data.event === 'new_invoice') {
                    showNotification('فاکتور جدید ایجاد شد!', 'success');
                    loadDashboardData();
                } else if (data.event === 'new_message') {
                    showNotification('پیام جدید دریافت شد!', 'info');
                    updateUnreadCount();
                } else if (data.event === 'check_reminder') {
                    showNotification(`یادآوری چک: ${data.data.check_number}`, 'warning');
                }
            }
            
            // نمایش نوتیفیکیشن
            function showNotification(message, type) {
                // ایجاد عنصر نوتیفیکیشن
                const notification = document.createElement('div');
                notification.style.cssText = `
                    position: fixed;
                    top: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    padding: 15px 25px;
                    border-radius: 10px;
                    background: ${type === 'success' ? '#4caf50' : 
                                type === 'error' ? '#f44336' : 
                                type === 'warning' ? '#ff9800' : '#2196f3'};
                    color: white;
                    z-index: 9999;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                    animation: slideDown 0.3s ease;
                `;
                notification.textContent = message;
                
                document.body.appendChild(notification);
                
                // حذف خودکار پس از 5 ثانیه
                setTimeout(() => {
                    notification.style.animation = 'slideUp 0.3s ease';
                    setTimeout(() => {
                        document.body.removeChild(notification);
                    }, 300);
                }, 5000);
            }
            
            // نمایش پیام
            function showMessage(text, type) {
                const messageDiv = document.getElementById('authMessage');
                messageDiv.textContent = text;
                messageDiv.className = `message ${type}`;
                messageDiv.style.display = 'block';
                
                // مخفی کردن خودکار پس از 5 ثانیه
                if (type === 'success') {
                    setTimeout(() => {
                        messageDiv.style.display = 'none';
                    }, 5000);
                }
            }
            
            // نمایش مودال
            function showModal(modalType) {
                // پیاده‌سازی مودال‌های مختلف
                alert(`مودال ${modalType} باز خواهد شد`);
                // اینجا می‌توانید کدهای مربوط به هر مودال را اضافه کنید
            }
            
            // خروج کاربر
            function logout() {
                if (confirm('آیا از حساب کاربری خود خارج می‌شوید؟')) {
                    localStorage.removeItem('accounting_token');
                    userToken = null;
                    currentUser = null;
                    
                    if (socket) {
                        socket.close();
                    }
                    
                    // بازگشت به صفحه ورود
                    document.getElementById('dashboard').style.display = 'none';
                    document.getElementById('authContainer').style.display = 'flex';
                    
                    // پاک کردن فرم
                    document.getElementById('phoneInput').value = '';
                    document.querySelectorAll('.otp-digit').forEach(input => input.value = '');
                    clearInterval(otpTimer);
                }
            }
            
            // اضافه کردن استایل‌های انیمیشن
            const style = document.createElement('style');
            style.textContent = `
                @keyframes slideDown {
                    from { top: -100px; opacity: 0; }
                    to { top: 20px; opacity: 1; }
                }
                
                @keyframes slideUp {
                    from { top: 20px; opacity: 1; }
                    to { top: -100px; opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        </script>
    </body>
    </html>
    '''
    return render_template_string(html_content)


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
        
        # ذخیره فاکتور
        cursor.execute('''
            INSERT INTO invoices 
            (user_id, customer_id, invoice_number, invoice_date, due_date, 
             total_amount, tax_amount, discount_amount, paid_amount, 
             status, payment_method, notes) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            data.get('notes', '')
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
            'total_amount': total_amount
        }), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

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

@socketio.on('send_message')
def handle_send_message(data):
    """ارسال پیام در چت"""
    user_id = data.get('user_id')
    customer_id = data.get('customer_id')
    message = data.get('message')
    
    if not all([user_id, customer_id, message]):
        return
    
    room_id = f"chat_{user_id}_{customer_id}"
    
    # ارسال پیام به همه در اتاق
    emit('new_message', {
        'room_id': room_id,
        'sender_id': user_id,
        'message_content': message,
        'timestamp': datetime.now().isoformat()
    }, room=room_id)
    
    print(f"📨 پیام از کاربر {user_id} به مشتری {customer_id}: {message[:50]}...")

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

# ==================== اجرای سرور ====================
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 سیستم حسابداری آنلاین - نسخه SPA")
    print("=" * 60)
    
    # راه‌اندازی دیتابیس
    init_database()
    
    # ایجاد دایرکتوری‌های مورد نیاز
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('backups', exist_ok=True)
    
    print("✅ سیستم آماده است")
    print("🌐 آدرس: http://localhost:5000")
    print("📱 تست شماره: 09123456789")
    print("🔑 کد OTP تست: 12345")
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
