// متغیرهای جهانی
let game;
let DEBUG_MODE = false;

// کلاس صحنه اصلی بازی
class MainScene {
    constructor() {
        this.player = null;
        this.bullets = [];
        this.level = null;
        this.particles = [];
    }
    
    enter() {
        console.log('Main scene entered');
        
        // ایجاد بازیکن
        this.player = new Player(game);
        this.player.game = game;
        
        // ایجاد سطح اول
        this.level = new Level(game, 1);
        
        // شروع موسیقی
        game.audioManager.playMusic('background', 0.3);
        
        // نمایش اطلاعیه شروع
        game.uiManager.showLevelStart(1);
    }
    
    exit() {
        console.log('Main scene exited');
        game.audioManager.stopMusic();
    }
    
    update(deltaTime) {
        // به روز رسانی بازیکن
        if (this.player) {
            this.player.update(deltaTime);
        }
        
        // به روز رسانی گلوله‌ها
        for (let i = this.bullets.length - 1; i >= 0; i--) {
            const bullet = this.bullets[i];
            bullet.update(deltaTime);
            
            if (bullet.life <= 0) {
                this.bullets.splice(i, 1);
            }
        }
        
        // به روز رسانی سطح
        if (this.level) {
            this.level.update(deltaTime);
        }
        
        // به روز رسانی ذرات
        game.renderer.updateParticles(deltaTime);
        
        // به روز رسانی اطلاعیه‌ها
        game.uiManager.updateNotifications(deltaTime);
    }
    
    render(ctx) {
        // رندر سطح (پس‌زمینه و دشمنان)
        if (this.level) {
            this.level.render(ctx);
        }
        
        // رندر گلوله‌ها
        this.bullets.forEach(bullet => {
            bullet.render(ctx);
        });
        
        // رندر بازیکن
        if (this.player) {
            this.player.render(ctx);
        }
        
        // رندر ذرات
        game.renderer.renderParticles();
        
        // رندر رابط کاربری
        game.uiManager.render(ctx);
    }
    
    addBullet(bullet) {
        bullet.game = game;
        this.bullets.push(bullet);
    }
    
    resize(width, height) {
        // مدیریت تغییر سایز (در صورت نیاز)
    }
}

// تابع مقداردهی اولیه بازی
async function initGame() {
    try {
        console.log('Initializing game...');
        
        // ایجاد موتور بازی
        game = new GameEngine();
        
        // اضافه کردن مدیران
        game.physics = new Physics();
        game.renderer = new Renderer(game.ctx);
        game.inputManager = new InputManager();
        game.audioManager = new AudioManager();
        game.assetManager = new AssetManager();
        game.gameManager = new GameManager(game);
        game.uiManager = new UIManager(game);
        
        // بارگذاری assets
        await game.assetManager.loadAll();
        
        // ایجاد و اضافه کردن صحنه اصلی
        const mainScene = new MainScene();
        game.addScene('main', mainScene);
        
        // شروع بازی
        game.gameManager.showMainMenu();
        
        console.log('Game initialized successfully');
        
    } catch (error) {
        console.error('Game initialization failed:', error);
        alert('خطا در راه‌اندازی بازی. لطفاً صفحه را مجدداً بارگذاری کنید.');
    }
}

// رویداد بارگذاری صفحه
window.addEventListener('DOMContentLoaded', initGame);

// رویدادهای دبیاگ (فقط در حالت توسعه)
window.addEventListener('keydown', (e) => {
    if (e.code === 'F3') {
        DEBUG_MODE = !DEBUG_MODE;
        console.log('DEBUG MODE:', DEBUG_MODE);
    }
    
    if (e.code === 'Escape') {
        if (game.gameManager.state === 'playing') {
            game.gameManager.pauseGame();
        } else if (game.gameManager.state === 'paused') {
            game.gameManager.resumeGame();
        }
    }
});

// رویداد قبل از بسته شدن صفحه
window.addEventListener('beforeunload', (e) => {
    if (game && game.gameManager.state === 'playing') {
        game.gameManager.saveGame();
    }
});

// Service Worker برای PWA (اختیاری)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('SW registered: ', registration);
            })
            .catch(registrationError => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}
