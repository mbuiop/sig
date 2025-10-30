class GameManager {
    constructor(game) {
        this.game = game;
        this.state = 'menu'; // menu, playing, paused, gameOver
        this.currentLevel = 1;
        this.score = 0;
        this.highScore = this.loadHighScore();
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.showMainMenu();
    }
    
    setupEventListeners() {
        // دکمه شروع بازی
        document.getElementById('startBtn').addEventListener('click', () => {
            this.startGame();
        });
        
        // دکمه ادامه بازی
        document.getElementById('continueBtn').addEventListener('click', () => {
            this.continueGame();
        });
        
        // دکمه تنظیمات
        document.getElementById('settingsBtn').addEventListener('click', () => {
            this.showSettings();
        });
        
        // دکمه درباره بازی
        document.getElementById('aboutBtn').addEventListener('click', () => {
            this.showAbout();
        });
        
        // دکمه‌های صفحه مکث
        document.getElementById('resumeBtn').addEventListener('click', () => {
            this.resumeGame();
        });
        
        document.getElementById('restartBtn').addEventListener('click', () => {
            this.restartGame();
        });
        
        document.getElementById('mainMenuBtn').addEventListener('click', () => {
            this.showMainMenu();
        });
        
        // دکمه‌های صفحه پایان بازی
        document.getElementById('retryBtn').addEventListener('click', () => {
            this.restartGame();
        });
        
        document.getElementById('gameOverMenuBtn').addEventListener('click', () => {
            this.showMainMenu();
        });
        
        // دکمه‌های لمسی
        document.getElementById('shootBtn').addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.game.inputManager.keys['Space'] = true;
        });
        
        document.getElementById('shootBtn').addEventListener('touchend', (e) => {
            e.preventDefault();
            this.game.inputManager.keys['Space'] = false;
        });
        
        document.getElementById('specialBtn').addEventListener('touchstart', (e) => {
            e.preventDefault();
            // فعال کردن قدرت ویژه
        });
        
        // رویداد کلیک خارج از بازی برای مکث
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.state === 'playing') {
                this.pauseGame();
            }
        });
    }
    
    startGame() {
        this.state = 'playing';
        this.currentLevel = 1;
        this.score = 0;
        
        this.hideAllScreens();
        document.getElementById('gameScreen').classList.remove('hidden');
        
        // شروع موسیقی بازی
        this.game.audioManager.playMusic('background', 0.3);
        
        // شروع صحنه بازی
        this.game.setScene('main');
        
        console.log('Game started');
    }
    
    continueGame() {
        // ادامه بازی از آخرین ذخیره
        const savedGame = this.loadGame();
        if (savedGame) {
            this.state = 'playing';
            this.currentLevel = savedGame.level;
            this.score = savedGame.score;
            
            this.hideAllScreens();
            document.getElementById('gameScreen').classList.remove('hidden');
            
            this.game.audioManager.playMusic('background', 0.3);
            this.game.setScene('main');
            
            console.log('Game continued from save');
        } else {
            alert('هیچ بازی ذخیره‌شده‌ای یافت نشد!');
        }
    }
    
    pauseGame() {
        if (this.state === 'playing') {
            this.state = 'paused';
            this.game.stop();
            
            this.hideAllScreens();
            document.getElementById('pauseScreen').classList.remove('hidden');
            
            console.log('Game paused');
        }
    }
    
    resumeGame() {
        if (this.state === 'paused') {
            this.state = 'playing';
            
            this.hideAllScreens();
            document.getElementById('gameScreen').classList.remove('hidden');
            
            this.game.start();
            
            console.log('Game resumed');
        }
    }
    
    restartGame() {
        this.startGame();
    }
    
    gameOver() {
        this.state = 'gameOver';
        this.game.stop();
        
        // به روز رسانی امتیاز نهایی
        document.getElementById('finalScore').textContent = this.score;
        
        // بررسی رکورد جدید
        if (this.score > this.highScore) {
            this.highScore = this.score;
            this.saveHighScore();
        }
        
        this.hideAllScreens();
        document.getElementById('gameOverScreen').classList.remove('hidden');
        
        // پخش صدای پایان بازی
        this.game.audioManager.playSound('gameOver');
        
        console.log('Game over');
    }
    
    levelComplete() {
        this.currentLevel++;
        this.score += this.currentLevel * 1000;
        
        // نمایش صفحه تکمیل مرحله
        setTimeout(() => {
            alert(`مرحله ${this.currentLevel - 1} تکمیل شد! آماده مرحله بعدی هستید؟`);
            this.saveGame();
        }, 1000);
    }
    
    showMainMenu() {
        this.state = 'menu';
        this.game.stop();
        
        this.hideAllScreens();
        document.getElementById('mainScreen').classList.remove('hidden');
        
        // توقف موسیقی بازی
        this.game.audioManager.stopMusic();
        
        console.log('Main menu shown');
    }
    
    showSettings() {
        // نمایش تنظیمات (می‌توانید این بخش را توسعه دهید)
        alert('منوی تنظیمات - این بخش قابل توسعه است');
    }
    
    showAbout() {
        // نمایش درباره بازی
        alert('نبرد کهکشانی\nیک بازی اکشن جنگی با گرافیک سینمایی\nساخته شده با HTML5 Canvas');
    }
    
    hideAllScreens() {
        const screens = document.querySelectorAll('.screen');
        screens.forEach(screen => {
            screen.classList.add('hidden');
        });
    }
    
    saveGame() {
        const gameData = {
            level: this.currentLevel,
            score: this.score,
            timestamp: Date.now()
        };
        
        localStorage.setItem('galacticWarfare_save', JSON.stringify(gameData));
    }
    
    loadGame() {
        const saved = localStorage.getItem('galacticWarfare_save');
        return saved ? JSON.parse(saved) : null;
    }
    
    saveHighScore() {
        localStorage.setItem('galacticWarfare_highscore', this.highScore);
    }
    
    loadHighScore() {
        return parseInt(localStorage.getItem('galacticWarfare_highscore') || '0');
    }
    
    updateHUD() {
        document.getElementById('score').textContent = this.score;
        document.getElementById('level').textContent = this.currentLevel;
        
        if (this.game.player) {
            document.getElementById('healthFill').style.width = 
                (this.game.player.health / this.game.player.maxHealth) * 100 + '%';
        }
    }
}
