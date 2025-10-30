class Player {
    constructor(game) {
        this.game = game;
        this.x = game.width / 2;
        this.y = game.height / 2;
        this.width = 50;
        this.height = 50;
        this.speed = 5;
        this.health = 100;
        this.maxHealth = 100;
        this.score = 0;
        this.weapon = 'plasma';
        this.weaponLevel = 1;
        this.invincible = false;
        this.invincibleTimer = 0;
        
        // انیمیشن‌ها
        this.animations = {
            idle: { frames: 4, speed: 0.2 },
            move: { frames: 6, speed: 0.15 },
            shoot: { frames: 3, speed: 0.1 }
        };
        
        this.currentAnimation = 'idle';
        this.animationFrame = 0;
        this.animationTimer = 0;
        
        // فیرینگ
        this.shootCooldown = 0;
        this.shootRate = 0.2; // shots per second
        
        // افکت‌های بصری
        this.trailParticles = [];
        this.engineGlow = true;
    }
    
    update(deltaTime) {
        this.handleInput();
        this.updateAnimation(deltaTime);
        this.updateShooting(deltaTime);
        this.updateInvincibility(deltaTime);
        this.updateTrailParticles(deltaTime);
        
        // محدود کردن موقعیت به مرزهای صفحه
        this.x = Math.max(this.width/2, Math.min(this.x, this.game.width - this.width/2));
        this.y = Math.max(this.height/2, Math.min(this.y, this.game.height - this.height/2));
    }
    
    handleInput() {
        const input = this.game.inputManager;
        const joystick = input.getJoystickDirection();
        
        // حرکت با جویستیک یا کیبورد
        let moveX = 0;
        let moveY = 0;
        
        if (joystick.x !== 0 || joystick.y !== 0) {
            moveX = joystick.x * this.speed;
            moveY = joystick.y * this.speed;
        } else {
            if (input.isKeyPressed('ArrowLeft') || input.isKeyPressed('KeyA')) moveX = -this.speed;
            if (input.isKeyPressed('ArrowRight') || input.isKeyPressed('KeyD')) moveX = this.speed;
            if (input.isKeyPressed('ArrowUp') || input.isKeyPressed('KeyW')) moveY = -this.speed;
            if (input.isKeyPressed('ArrowDown') || input.isKeyPressed('KeyS')) moveY = this.speed;
        }
        
        // اعمال حرکت
        this.x += moveX;
        this.y += moveY;
        
        // تغییر انیمیشن بر اساس حرکت
        if (moveX !== 0 || moveY !== 0) {
            this.currentAnimation = 'move';
        } else {
            this.currentAnimation = 'idle';
        }
        
        // شلیک
        if (input.isPointerPressed() || input.isKeyPressed('Space')) {
            this.shoot();
        }
    }
    
    updateAnimation(deltaTime) {
        this.animationTimer += deltaTime;
        const animation = this.animations[this.currentAnimation];
        
        if (this.animationTimer >= animation.speed) {
            this.animationTimer = 0;
            this.animationFrame = (this.animationFrame + 1) % animation.frames;
        }
    }
    
    updateShooting(deltaTime) {
        if (this.shootCooldown > 0) {
            this.shootCooldown -= deltaTime;
        }
    }
    
    updateInvincibility(deltaTime) {
        if (this.invincible) {
            this.invincibleTimer -= deltaTime;
            if (this.invincibleTimer <= 0) {
                this.invincible = false;
            }
        }
    }
    
    updateTrailParticles(deltaTime) {
        // ایجاد ذرات دنباله
        if (this.currentAnimation === 'move') {
            this.trailParticles.push({
                x: this.x,
                y: this.y + this.height/2,
                size: Math.random() * 3 + 1,
                life: 1,
                color: '#2196f3'
            });
        }
        
        // به روز رسانی ذرات
        for (let i = this.trailParticles.length - 1; i >= 0; i--) {
            const particle = this.trailParticles[i];
            particle.life -= 0.05;
            particle.y += 2;
            
            if (particle.life <= 0) {
                this.trailParticles.splice(i, 1);
            }
        }
    }
    
    shoot() {
        if (this.shootCooldown > 0) return;
        
        this.shootCooldown = 1 / this.shootRate;
        this.currentAnimation = 'shoot';
        this.animationFrame = 0;
        
        // ایجاد گلوله
        const bullet = new Bullet(
            this.x,
            this.y - this.height/2,
            0,
            -10,
            this.weaponLevel
        );
        
        this.game.currentScene.addBullet(bullet);
        
        // پخش صدا
        this.game.audioManager.playSound('shoot');
        
        // افکت شلیک
        this.game.renderer.createExplosion(
            this.x,
            this.y - this.height/2,
            10,
            '#2196f3'
        );
    }
    
    takeDamage(amount) {
        if (this.invincible) return;
        
        this.health -= amount;
        this.invincible = true;
        this.invincibleTimer = 1; // 1 second invincibility
        
        // افکت آسیب
        this.game.renderer.createExplosion(this.x, this.y, 20, '#ff3d00');
        this.game.audioManager.playSound('hit');
        
        if (this.health <= 0) {
            this.die();
        }
    }
    
    die() {
        // افکت مرگ
        this.game.renderer.createExplosion(this.x, this.y, 50, '#ff6b00');
        this.game.audioManager.playSound('explosion');
        
        // پایان بازی
        this.game.gameManager.gameOver();
    }
    
    heal(amount) {
        this.health = Math.min(this.maxHealth, this.health + amount);
    }
    
    upgradeWeapon() {
        this.weaponLevel = Math.min(5, this.weaponLevel + 1);
        this.shootRate += 0.1;
    }
    
    render(ctx) {
        const renderer = this.game.renderer;
        
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
        
        // رندر بازیکن
        const alpha = this.invincible ? (Math.sin(Date.now() / 100) * 0.5 + 0.5) : 1;
        
        // بدنه اصلی
        ctx.save();
        ctx.globalAlpha = alpha;
        
        // گرادیانت برای بازیکن
        const gradient = ctx.createLinearGradient(
            this.x - this.width/2, this.y - this.height/2,
            this.x + this.width/2, this.y + this.height/2
        );
        gradient.addColorStop(0, '#2196f3');
        gradient.addColorStop(1, '#1976d2');
        
        ctx.fillStyle = gradient;
        ctx.fillRect(
            this.x - this.width/2,
            this.y - this.height/2,
            this.width,
            this.height
        );
        
        // جزئیات بازیکن
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(
            this.x - 10,
            this.y - 15,
            20,
            10
        );
        
        // موتورها
        if (this.engineGlow) {
            const engineAlpha = Math.sin(Date.now() / 100) * 0.3 + 0.7;
            ctx.fillStyle = `rgba(33, 150, 243, ${engineAlpha})`;
            ctx.fillRect(
                this.x - 15,
                this.y + this.height/2 - 5,
                10,
                15
            );
            ctx.fillRect(
                this.x + 5,
                this.y + this.height/2 - 5,
                10,
                15
            );
        }
        
        ctx.restore();
        
        // نمایش سلامتی
        renderer.drawHealthBar(
            this.x - 25,
            this.y - 40,
            50,
            5,
            this.health,
            this.maxHealth
        );
    }
          }
