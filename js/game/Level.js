class Level {
    constructor(game, number) {
        this.game = game;
        this.number = number;
        this.enemies = [];
        this.spawnTimer = 0;
        this.spawnRate = 2; // seconds between spawns
        this.enemiesKilled = 0;
        this.enemiesToKill = 10 + (number * 5);
        this.completed = false;
        
        // تنظیمات سطح بر اساس شماره
        this.difficulty = Math.min(10, number);
        this.backgroundSpeed = 0.5 + (number * 0.1);
        
        // ستاره‌های پس‌زمینه
        this.stars = this.generateStars(100);
    }
    
    generateStars(count) {
        const stars = [];
        for (let i = 0; i < count; i++) {
            stars.push({
                x: Math.random() * this.game.width,
                y: Math.random() * this.game.height,
                size: Math.random() * 2 + 0.5,
                speed: Math.random() * 2 + 0.5,
                brightness: Math.random() * 0.8 + 0.2
            });
        }
        return stars;
    }
    
    update(deltaTime) {
        this.updateStars(deltaTime);
        this.updateEnemies(deltaTime);
        this.updateSpawning(deltaTime);
        this.checkCompletion();
    }
    
    updateStars(deltaTime) {
        this.stars.forEach(star => {
            star.y += star.speed * this.backgroundSpeed;
            if (star.y > this.game.height) {
                star.y = 0;
                star.x = Math.random() * this.game.width;
            }
        });
    }
    
    updateEnemies(deltaTime) {
        for (let i = this.enemies.length - 1; i >= 0; i--) {
            const enemy = this.enemies[i];
            enemy.update(deltaTime, this.game.player);
            
            // بررسی برخورد با گلوله‌ها
            for (let j = this.game.bullets.length - 1; j >= 0; j--) {
                const bullet = this.game.bullets[j];
                if (this.checkCollision(enemy, bullet)) {
                    if (enemy.takeDamage(bullet.damage)) {
                        // نابودی دشمن
                        this.enemies.splice(i, 1);
                        this.enemiesKilled++;
                        this.game.player.score += enemy.scoreValue;
                        
                        // افکت انفجار
                        this.game.renderer.createExplosion(
                            enemy.x, enemy.y, 
                            enemy.width, 
                            '#ff6b00'
                        );
                        
                        // پخش صدا
                        this.game.audioManager.playSound('explosion');
                        
                        // شانس افتادن پاورآپ
                        if (Math.random() < 0.2) {
                            this.spawnPowerUp(enemy.x, enemy.y);
                        }
                    }
                    
                    // حذف گلوله
                    this.game.bullets.splice(j, 1);
                    break;
                }
            }
            
            // بررسی برخورد با بازیکن
            if (this.checkCollision(enemy, this.game.player)) {
                this.game.player.takeDamage(10);
            }
        }
    }
    
    updateSpawning(deltaTime) {
        if (this.completed) return;
        
        this.spawnTimer += deltaTime;
        if (this.spawnTimer >= this.spawnRate) {
            this.spawnTimer = 0;
            this.spawnEnemy();
        }
    }
    
    spawnEnemy() {
        if (this.enemies.length >= 5 + this.difficulty) return;
        
        const x = Math.random() * this.game.width;
        const y = -50;
        
        // انتخاب نوع دشمن بر اساس سطح
        let type = 'basic';
        const rand = Math.random();
        
        if (this.number >= 3 && rand < 0.2) {
            type = 'fast';
        } else if (this.number >= 5 && rand < 0.15) {
            type = 'tank';
        } else if (this.number >= 10 && rand < 0.1) {
            type = 'boss';
        }
        
        const enemy = new Enemy(x, y, type);
        enemy.game = this.game;
        this.enemies.push(enemy);
    }
    
    spawnPowerUp(x, y) {
        // ایجاد پاورآپ (می‌توانید این بخش را توسعه دهید)
        console.log('PowerUp spawned at:', x, y);
    }
    
    checkCollision(obj1, obj2) {
        return this.game.physics.rectCollision(
            obj1.x - obj1.width/2, obj1.y - obj1.height/2,
            obj1.width, obj1.height,
            obj2.x - obj2.width/2, obj2.y - obj2.height/2,
            obj2.width, obj2.height
        );
    }
    
    checkCompletion() {
        if (!this.completed && this.enemiesKilled >= this.enemiesToKill) {
            this.completed = true;
            this.game.gameManager.levelComplete();
        }
    }
    
    render(ctx) {
        this.renderBackground(ctx);
        this.renderEnemies(ctx);
    }
    
    renderBackground(ctx) {
        // پس‌زمینه فضایی
        ctx.fillStyle = '#0c0c2e';
        ctx.fillRect(0, 0, this.game.width, this.game.height);
        
        // ستاره‌ها
        this.stars.forEach(star => {
            ctx.save();
            ctx.globalAlpha = star.brightness;
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(star.x, star.y, star.size, star.size);
            ctx.restore();
        });
        
        // سحابی‌های رنگی
        this.renderNebulae(ctx);
    }
    
    renderNebulae(ctx) {
        // سحابی آبی
        const blueNebula = ctx.createRadialGradient(
            this.game.width * 0.7, this.game.height * 0.3, 0,
            this.game.width * 0.7, this.game.height * 0.3, 300
        );
        blueNebula.addColorStop(0, 'rgba(33, 150, 243, 0.3)');
        blueNebula.addColorStop(1, 'transparent');
        
        ctx.fillStyle = blueNebula;
        ctx.fillRect(0, 0, this.game.width, this.game.height);
        
        // سحابی بنفش
        const purpleNebula = ctx.createRadialGradient(
            this.game.width * 0.3, this.game.height * 0.7, 0,
            this.game.width * 0.3, this.game.height * 0.7, 400
        );
        purpleNebula.addColorStop(0, 'rgba(156, 39, 176, 0.2)');
        purpleNebula.addColorStop(1, 'transparent');
        
        ctx.fillStyle = purpleNebula;
        ctx.fillRect(0, 0, this.game.width, this.game.height);
    }
    
    renderEnemies(ctx) {
        this.enemies.forEach(enemy => {
            enemy.render(ctx);
        });
    }
}
