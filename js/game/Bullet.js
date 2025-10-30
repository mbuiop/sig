class Bullet {
    constructor(x, y, vx, vy, level = 1) {
        this.x = x;
        this.y = y;
        this.vx = vx;
        this.vy = vy;
        this.level = level;
        this.damage = 10 * level;
        this.life = 1;
        
        // تنظیمات بر اساس سطح سلاح
        switch (level) {
            case 1:
                this.width = 5;
                this.height = 15;
                this.color = '#2196f3';
                this.speed = 8;
                break;
            case 2:
                this.width = 7;
                this.height = 20;
                this.color = '#4caf50';
                this.speed = 9;
                this.damage = 15;
                break;
            case 3:
                this.width = 10;
                this.height = 25;
                this.color = '#ff9800';
                this.speed = 10;
                this.damage = 25;
                break;
            case 4:
                this.width = 12;
                this.height = 30;
                this.color = '#f44336';
                this.speed = 11;
                this.damage = 40;
                break;
            case 5:
                this.width = 15;
                this.height = 35;
                this.color = '#9c27b0';
                this.speed = 12;
                this.damage = 60;
                break;
        }
        
        // اعمال سرعت
        this.vx *= this.speed;
        this.vy *= this.speed;
        
        // ذرات دنباله
        this.trailParticles = [];
    }
    
    update(deltaTime) {
        // حرکت
        this.x += this.vx;
        this.y += this.vy;
        
        // ایجاد ذرات دنباله
        this.trailParticles.push({
            x: this.x,
            y: this.y,
            size: Math.random() * 2 + 1,
            life: 1,
            color: this.color
        });
        
        // به روز رسانی ذرات
        for (let i = this.trailParticles.length - 1; i >= 0; i--) {
            const particle = this.trailParticles[i];
            particle.life -= 0.1;
            particle.x -= this.vx * 0.1;
            particle.y -= this.vy * 0.1;
            
            if (particle.life <= 0) {
                this.trailParticles.splice(i, 1);
            }
        }
        
        // بررسی خروج از صفحه
        if (this.x < -100 || this.x > this.game.width + 100 ||
            this.y < -100 || this.y > this.game.height + 100) {
            this.life = 0;
        }
    }
    
    render(ctx) {
        // رندر ذرات دنباله
        this.trailParticles.forEach(particle => {
            ctx.save();
            ctx.globalAlpha = particle.life;
            ctx.fillStyle = particle.color;
            ctx.fillRect(
                particle.x - particle.size/2,
                particle.y - particle.size/2,
                particle.size,
                particle.size
            );
            ctx.restore();
        });
        
        // رندر گلوله اصلی
        ctx.save();
        
        // گرادیانت برای گلوله
        const gradient = ctx.createLinearGradient(
            this.x - this.width/2, this.y - this.height/2,
            this.x + this.width/2, this.y + this.height/2
        );
        gradient.addColorStop(0, this.color);
        gradient.addColorStop(1, this.lightenColor(this.color, 0.5));
        
        ctx.fillStyle = gradient;
        ctx.fillRect(
            this.x - this.width/2,
            this.y - this.height/2,
            this.width,
            this.height
        );
        
        // هسته درخشان
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(
            this.x - this.width/4,
            this.y - this.height/4,
            this.width/2,
            this.height/2
        );
        
        ctx.restore();
    }
    
    lightenColor(color, factor) {
        // روشن کردن رنگ
        const hex = color.replace('#', '');
        const num = parseInt(hex, 16);
        const amt = Math.round(2.55 * factor * 100);
        const R = (num >> 16) + amt;
        const G = (num >> 8 & 0x00FF) + amt;
        const B = (num & 0x0000FF) + amt;
        return "#" + (
            0x1000000 +
            (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
            (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
            (B < 255 ? B < 1 ? 0 : B : 255)
        ).toString(16).slice(1);
    }
    }
