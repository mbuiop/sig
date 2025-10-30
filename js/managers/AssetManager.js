class AssetManager {
    constructor() {
        this.images = {};
        this.sounds = {};
        this.loaded = false;
        this.loadProgress = 0;
        this.totalAssets = 0;
        this.loadedAssets = 0;
    }
    
    async loadAll() {
        const assets = {
            images: [
                { name: 'player', path: 'assets/images/player.png' },
                { name: 'enemy_basic', path: 'assets/images/enemy_basic.png' },
                { name: 'enemy_fast', path: 'assets/images/enemy_fast.png' },
                { name: 'enemy_tank', path: 'assets/images/enemy_tank.png' },
                { name: 'enemy_boss', path: 'assets/images/enemy_boss.png' },
                { name: 'bullet', path: 'assets/images/bullet.png' },
                { name: 'background', path: 'assets/images/background.jpg' },
                { name: 'explosion', path: 'assets/images/explosion.png' }
            ],
            sounds: [
                { name: 'shoot', path: 'assets/audio/laser.mp3' },
                { name: 'explosion', path: 'assets/audio/explosion.mp3' },
                { name: 'hit', path: 'assets/audio/hit.mp3' },
                { name: 'powerup', path: 'assets/audio/powerup.mp3' },
                { name: 'gameover', path: 'assets/audio/gameover.mp3' },
                { name: 'background', path: 'assets/audio/background.mp3' }
            ]
        };
        
        this.totalAssets = assets.images.length + assets.sounds.length;
        
        try {
            // بارگذاری تصاویر
            await Promise.all(assets.images.map(asset => this.loadImage(asset)));
            
            // بارگذاری صداها
            await Promise.all(assets.sounds.map(asset => this.loadSound(asset)));
            
            this.loaded = true;
            console.log('All assets loaded successfully');
        } catch (error) {
            console.error('Error loading assets:', error);
        }
    }
    
    loadImage(asset) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                this.images[asset.name] = img;
                this.assetLoaded();
                resolve(img);
            };
            img.onerror = reject;
            img.src = asset.path;
        });
    }
    
    loadSound(asset) {
        return new Promise((resolve, reject) => {
            const audio = new Audio();
            audio.addEventListener('canplaythrough', () => {
                this.sounds[asset.name] = audio;
                this.assetLoaded();
                resolve(audio);
            });
            audio.addEventListener('error', reject);
            audio.src = asset.path;
            audio.preload = 'auto';
        });
    }
    
    assetLoaded() {
        this.loadedAssets++;
        this.loadProgress = (this.loadedAssets / this.totalAssets) * 100;
        
        // به روز رسانی نوار پیشرفت (اگر وجود داشته باشد)
        const progressBar = document.getElementById('loadProgress');
        if (progressBar) {
            progressBar.style.width = this.loadProgress + '%';
        }
    }
    
    getImage(name) {
        return this.images[name];
    }
    
    getSound(name) {
        return this.sounds[name];
    }
    
    isLoaded() {
        return this.loaded;
    }
    
    getProgress() {
        return this.loadProgress;
    }
          }
