class Enemy {
    constructor(x, y, type = 'basic') {
        this.x = x;
        this.y = y;
        this.type = type;
        this.width = 40;
        this.height = 40;
        this.speed = 2;
        this.health = 50;
        this.maxHealth = 50;
        this.scoreValue = 100;
        this.attackCooldown = 0;
        this.attackRate = 1;
        
        // تنظیمات بر اساس نوع دشمن
        switch (type) {
            case 'fast':
                this.speed = 4;
                this.health = 30;
                this.scoreValue = 150;
                this.width = 30;
                this.height = 30;
                break;
            case 'tank':
                this.speed = 1;
                this.health = 150;
                this.maxHealth = 150;
                this.scoreValue = 300;
                this.width = 60;
                this.height = 60;
                break;
            case 'boss':
                this.speed = 1.5;
                this.health = 500;
                this.maxHealth = 500;
                this.scoreValue = 1000;
                this.width = 100;
                this.height = 100;
                this.attackRate = 2;
                break;
        }
        
        // انیمیشن‌ها
        this.animationFrame = 0;
        this.animationTimer = 0;
        this.animationSpeed = 0.2;
    }
    
    update(deltaTime, player) {
        // حرکت به سمت بازیکن
        const dx = player.x - this.x;
        const dy = player.y - this.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance > 0) {
            this.x += (dx / distance) * this.speed;
            this.y += (dy / distance) * this.speed;
        }
        
        // به روز رسانی انیمیشن
        this.animationTimer += deltaTime;
        if (this.animationTimer >= this.animationSpeed) {
            this.animationTimer = 0;
            this.animationFrame = (this.animationFrame + 1) % 4;
        }
        
        // به روز رسانی کوئلدون حمله
        if (this.attackCooldown > 0) {
            this.attackCooldown -= deltaTime;
        }
        
        // حمله به بازیکن اگر نزدیک باشد
        if (distance < 50 && this.attackCooldown <= 0) {
            this.attack(player);
            this.attackCooldown = 1 / this.attackRate;
        }
    }
    
    attack(player) {
        player.takeDamage(10);
        
        // افکت حمله
        if (this.game) {
            this.game.renderer.createExplosion(player.x, player.y, 15, '#ff3d00');
        }
    }
    
    takeDamage(amount) {
        this.health -= amount;
        
        // افکت آسیب
        if (this.game) {
            this.game.renderer.createExplosion(this.x, this.y, 15, '#ff6b00');
            this.game.audioManager.playSound('hit');
        }
        
        return this.health <= 0;
    }
    
    render(ctx) {
        const renderer = this.game?.renderer;
        
        // رنگ بر اساس نوع دشمن
        let color;
        switch (this.type) {
            case 'basic':
                color = '#f44336';
                break;
            case 'fast':
                color = '#ff9800';
                break;
            case 'tank':
                color = '#795548';
                break;
            case 'boss':
                color = '#9c27b0';
                break;
        }
        
        // بدنه اصلی دشمن
        ctx.save();
        
        // گرادیانت برای دشمن
        const gradient = ctx.createLinearGradient(
            this.x - this.width/2, this.y - this.height/2,
            this.x + this.width/2, this.y + this.height/2
        );
        gradient.addColorStop(0, color);
        gradient.addColorStop(1, this.darkenColor(color, 0.3));
        
        ctx.fillStyle = gradient;
        ctx.fillRect(
            this.x - this.width/2,
            this.y - this.height/2,
            this.width,
            this.height
        );
        
        // جزئیات دشمن
        ctx.fillStyle = '#000000';
        ctx.fillRect(
            this.x - 8,
            this.y - 8,
            16,
            16
        );
        
        // چشم‌ها (انیمیشن)
        const eyeOffset = this.animationFrame * 2 - 3;
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(
            this.x - 15 + eyeOffset,
            this.y - 10,
            5,
            5
        );
        ctx.fillRect(
            this.x + 10 + eyeOffset,
            this.y - 10,
            5,
            5
        );
        
        ctx.restore();
        
        // نوار سلامتی برای دشمنان قوی
        if (this.type === 'tank' || this.type === 'boss') {
            renderer.drawHealthBar(
                this.x - this.width/2,
                this.y - this.height/2 - 10,
                this.width,
                5,
                this.health,
                this.maxHealth,
                color
            );
        }
    }
    
    darkenColor(color, factor) {
        // تیره کردن رنگ
        const hex = color.replace('#', '');
        const num = parseInt(hex, 16);
        const amt = Math.round(2.55 * factor * 100);
        const R = (num >> 16) - amt;
        const G = (num >> 8 & 0x00FF) - amt;
        const B = (num & 0x0000FF) - amt;
        return "#" + (
            0x1000000 +
            (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
            (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
            (B < 255 ? B < 1 ? 0 : B : 255)
        ).toString(16).slice(1);
    }
          }
