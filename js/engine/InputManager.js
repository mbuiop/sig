class InputManager {
    constructor() {
        this.keys = {};
        this.mouse = {
            x: 0,
            y: 0,
            pressed: false
        };
        
        this.touch = {
            x: 0,
            y: 0,
            active: false
        };
        
        this.joystick = {
            active: false,
            x: 0,
            y: 0,
            baseX: 0,
            baseY: 0,
            radius: 50
        };
        
        this.init();
    }
    
    init() {
        // رویدادهای کیبورد
        document.addEventListener('keydown', (e) => {
            this.keys[e.code] = true;
        });
        
        document.addEventListener('keyup', (e) => {
            this.keys[e.code] = false;
        });
        
        // رویدادهای موس
        document.addEventListener('mousemove', (e) => {
            this.mouse.x = e.clientX;
            this.mouse.y = e.clientY;
        });
        
        document.addEventListener('mousedown', () => {
            this.mouse.pressed = true;
        });
        
        document.addEventListener('mouseup', () => {
            this.mouse.pressed = false;
        });
        
        // رویدادهای لمسی
        document.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.touch.active = true;
            this.touch.x = e.touches[0].clientX;
            this.touch.y = e.touches[0].clientY;
            
            // فعال کردن جویستیک
            this.activateJoystick(this.touch.x, this.touch.y);
        });
        
        document.addEventListener('touchmove', (e) => {
            e.preventDefault();
            if (this.touch.active) {
                this.touch.x = e.touches[0].clientX;
                this.touch.y = e.touches[0].clientY;
                
                // به روز رسانی جویستیک
                this.updateJoystick(this.touch.x, this.touch.y);
            }
        });
        
        document.addEventListener('touchend', () => {
            this.touch.active = false;
            this.deactivateJoystick();
        });
        
        // جلوگیری از اسکرول لمسی
        document.addEventListener('touchmove', (e) => {
            if (e.target.tagName !== 'CANVAS') return;
            e.preventDefault();
        }, { passive: false });
        
        console.log('Input Manager Initialized');
    }
    
    // فعال کردن جویستیک
    activateJoystick(x, y) {
        this.joystick.active = true;
        this.joystick.baseX = x;
        this.joystick.baseY = y;
        this.joystick.x = x;
        this.joystick.y = y;
        
        // نمایش جویستیک
        const joystickElement = document.getElementById('joystick');
        const joystickArea = document.querySelector('.joystick-area');
        
        if (joystickElement && joystickArea) {
            joystickArea.style.left = (x - 60) + 'px';
            joystickArea.style.bottom = '20px';
            joystickArea.style.display = 'flex';
        }
    }
    
    // به روز رسانی جویستیک
    updateJoystick(x, y) {
        if (!this.joystick.active) return;
        
        const dx = x - this.joystick.baseX;
        const dy = y - this.joystick.baseY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance > this.joystick.radius) {
            const angle = Math.atan2(dy, dx);
            this.joystick.x = this.joystick.baseX + Math.cos(angle) * this.joystick.radius;
            this.joystick.y = this.joystick.baseY + Math.sin(angle) * this.joystick.radius;
        } else {
            this.joystick.x = x;
            this.joystick.y = y;
        }
        
        // به روز رسانی موقعیت هندل جویستیک
        const joystickElement = document.getElementById('joystick');
        if (joystickElement) {
            const offsetX = this.joystick.x - this.joystick.baseX;
            const offsetY = this.joystick.y - this.joystick.baseY;
            joystickElement.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
        }
    }
    
    // غیر فعال کردن جویستیک
    deactivateJoystick() {
        this.joystick.active = false;
        this.joystick.x = this.joystick.baseX;
        this.joystick.y = this.joystick.baseY;
        
        // مخفی کردن جویستیک
        const joystickArea = document.querySelector('.joystick-area');
        if (joystickArea) {
            joystickArea.style.display = 'none';
        }
    }
    
    // دریافت جهت جویستیک
    getJoystickDirection() {
        if (!this.joystick.active) return { x: 0, y: 0 };
        
        const dx = this.joystick.x - this.joystick.baseX;
        const dy = this.joystick.y - this.joystick.baseY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < 10) return { x: 0, y: 0 };
        
        return {
            x: dx / this.joystick.radius,
            y: dy / this.joystick.radius
        };
    }
    
    // بررسی فشار دکمه
    isKeyPressed(code) {
        return this.keys[code] || false;
    }
    
    // دریافت موقعیت موس/لمس
    getPointerPosition() {
        if (this.touch.active) {
            return { x: this.touch.x, y: this.touch.y };
        }
        return { x: this.mouse.x, y: this.mouse.y };
    }
    
    // بررسی کلیک/لمس
    isPointerPressed() {
        return this.mouse.pressed || this.touch.active;
    }
    }
