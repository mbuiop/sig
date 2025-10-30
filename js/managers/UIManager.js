class UIManager {
    constructor(game) {
        this.game = game;
        this.notifications = [];
        this.notificationDuration = 3; // seconds
    }
    
    showNotification(text, type = 'info') {
        const notification = {
            id: Date.now(),
            text: text,
            type: type,
            life: this.notificationDuration,
            y: 100 + this.notifications.length * 60
        };
        
        this.notifications.push(notification);
        
        // حذف خودکار پس از مدت زمان مشخص
        setTimeout(() => {
            this.removeNotification(notification.id);
        }, this.notificationDuration * 1000);
        
        return notification.id;
    }
    
    removeNotification(id) {
        this.notifications = this.notifications.filter(n => n.id !== id);
    }
    
    updateNotifications(deltaTime) {
        for (let i = this.notifications.length - 1; i >= 0; i--) {
            const notification = this.notifications[i];
            notification.life -= deltaTime;
            
            if (notification.life <= 0) {
                this.notifications.splice(i, 1);
            }
        }
    }
    
    renderNotifications(ctx) {
        this.notifications.forEach(notification => {
            this.renderNotification(ctx, notification);
        });
    }
    
    renderNotification(ctx, notification) {
        const alpha = Math.min(1, notification.life * 2);
        const width = 300;
        const height = 50;
        const x = (this.game.width - width) / 2;
        const y = notification.y;
        
        ctx.save();
        ctx.globalAlpha = alpha;
        
        // پس‌زمینه
        ctx.fillStyle = this.getNotificationColor(notification.type);
        ctx.fillRect(x, y, width, height);
        
        // حاشیه
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, width, height);
        
        // متن
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 16px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(notification.text, x + width/2, y + height/2);
        
        ctx.restore();
    }
    
    getNotificationColor(type) {
        switch (type) {
            case 'success':
                return 'rgba(76, 175, 80, 0.9)';
            case 'warning':
                return 'rgba(255, 152, 0, 0.9)';
            case 'error':
                return 'rgba(244, 67, 54, 0.9)';
            default:
                return 'rgba(33, 150, 243, 0.9)';
        }
    }
    
    showLevelStart(level) {
        this.showNotification(`شروع مرحله ${level}`, 'info');
    }
    
    showLevelComplete(level) {
        this.showNotification(`مرحله ${level} تکمیل شد!`, 'success');
    }
    
    showPowerUp(type) {
        this.showNotification(`قدرت ${type} فعال شد!`, 'success');
    }
    
    updateHUD() {
        // به روز رسانی عناصر HUD
        const scoreElement = document.getElementById('score');
        const levelElement = document.getElementById('level');
        const healthFill = document.getElementById('healthFill');
        const weaponElement = document.getElementById('weapon');
        
        if (scoreElement && this.game.player) {
            scoreElement.textContent = this.game.player.score;
        }
        
        if (levelElement && this.game.gameManager) {
            levelElement.textContent = this.game.gameManager.currentLevel;
        }
        
        if (healthFill && this.game.player) {
            const healthPercent = (this.game.player.health / this.game.player.maxHealth) * 100;
            healthFill.style.width = healthPercent + '%';
        }
        
        if (weaponElement && this.game.player) {
            weaponElement.textContent = this.getWeaponName(this.game.player.weaponLevel);
        }
    }
    
    getWeaponName(level) {
        const names = ['پلاسما', 'لیزر', 'فوتون', 'کوانتوم', 'پادماده'];
        return names[level - 1] || names[0];
    }
    
    render(ctx) {
        this.updateHUD();
        this.renderNotifications(ctx);
    }
}
