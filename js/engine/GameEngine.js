class GameEngine {
    constructor() {
        this.canvas = document.getElementById('gameCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
        
        this.lastTime = 0;
        this.deltaTime = 0;
        this.fps = 0;
        this.frameCount = 0;
        this.fpsTimer = 0;
        
        this.scenes = {};
        this.currentScene = null;
        this.isRunning = false;
        
        this.init();
    }
    
    init() {
        // تنظیمات اولیه موتور بازی
        this.ctx.imageSmoothingEnabled = false;
        this.resize();
        
        // رویداد تغییر سایز
        window.addEventListener('resize', () => this.resize());
        
        console.log('Game Engine Initialized');
    }
    
    resize() {
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
        
        if (this.currentScene && this.currentScene.resize) {
            this.currentScene.resize(this.width, this.height);
        }
    }
    
    addScene(name, scene) {
        this.scenes[name] = scene;
        scene.game = this;
    }
    
    setScene(name) {
        if (this.scenes[name]) {
            if (this.currentScene && this.currentScene.exit) {
                this.currentScene.exit();
            }
            
            this.currentScene = this.scenes[name];
            
            if (this.currentScene.enter) {
                this.currentScene.enter();
            }
            
            return true;
        }
        return false;
    }
    
    start() {
        if (!this.isRunning) {
            this.isRunning = true;
            this.gameLoop();
        }
    }
    
    stop() {
        this.isRunning = false;
    }
    
    gameLoop(currentTime = 0) {
        if (!this.isRunning) return;
        
        // محاسبه deltaTime
        this.deltaTime = (currentTime - this.lastTime) / 1000;
        this.lastTime = currentTime;
        
        // محاسبه FPS
        this.frameCount++;
        this.fpsTimer += this.deltaTime;
        if (this.fpsTimer >= 1) {
            this.fps = this.frameCount;
            this.frameCount = 0;
            this.fpsTimer = 0;
        }
        
        // به روز رسانی و رندر
        this.update(this.deltaTime);
        this.render();
        
        requestAnimationFrame((time) => this.gameLoop(time));
    }
    
    update(deltaTime) {
        if (this.currentScene && this.currentScene.update) {
            this.currentScene.update(deltaTime);
        }
    }
    
    render() {
        // پاک کردن کانواس
        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, this.width, this.height);
        
        // رندر صحنه فعلی
        if (this.currentScene && this.currentScene.render) {
            this.currentScene.render(this.ctx);
        }
        
        // نمایش FPS (فقط در حالت توسعه)
        if (DEBUG_MODE) {
            this.ctx.fillStyle = 'white';
            this.ctx.font = '14px Arial';
            this.ctx.fillText(`FPS: ${this.fps}`, 10, 20);
        }
    }
}
