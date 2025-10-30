class Physics {
    constructor() {
        this.gravity = 0.5;
        this.friction = 0.97;
    }
    
    // تشخیص برخورد دایره‌ای
    circleCollision(x1, y1, r1, x2, y2, r2) {
        const dx = x1 - x2;
        const dy = y1 - y2;
        const distance = Math.sqrt(dx * dx + dy * dy);
        return distance < r1 + r2;
    }
    
    // تشخیص برخورد مستطیلی
    rectCollision(x1, y1, w1, h1, x2, y2, w2, h2) {
        return x1 < x2 + w2 &&
               x1 + w1 > x2 &&
               y1 < y2 + h2 &&
               y1 + h1 > y2;
    }
    
    // تشخیص برخورد نقطه با مستطیل
    pointInRect(px, py, x, y, w, h) {
        return px >= x && px <= x + w && py >= y && py <= y + h;
    }
    
    // محاسبه فاصله بین دو نقطه
    distance(x1, y1, x2, y2) {
        const dx = x2 - x1;
        const dy = y2 - y1;
        return Math.sqrt(dx * dx + dy * dy);
    }
    
    // محاسبه زاویه بین دو نقطه
    angleBetween(x1, y1, x2, y2) {
        return Math.atan2(y2 - y1, x2 - x1);
    }
    
    // حرکت به سمت هدف با سرعت مشخص
    moveTowards(current, target, speed) {
        const diff = target - current;
        if (Math.abs(diff) < speed) return target;
        return current + Math.sign(diff) * speed;
    }
    
    // محاسبه حرکت با شتاب
    accelerate(current, target, acceleration, maxSpeed) {
        let speed = current;
        if (speed < target) {
            speed = Math.min(speed + acceleration, target);
        } else if (speed > target) {
            speed = Math.max(speed - acceleration, target);
        }
        return Math.max(Math.min(speed, maxSpeed), -maxSpeed);
    }
    
    // محاسبه بردار حرکت با زاویه و سرعت
    getMovementVector(angle, speed) {
        return {
            x: Math.cos(angle) * speed,
            y: Math.sin(angle) * speed
        };
    }
    
    // محدود کردن موقعیت به مرزهای صفحه
    clampPosition(x, y, width, height, objectWidth, objectHeight) {
        return {
            x: Math.max(objectWidth/2, Math.min(x, width - objectWidth/2)),
            y: Math.max(objectHeight/2, Math.min(y, height - objectHeight/2))
        };
    }
}
