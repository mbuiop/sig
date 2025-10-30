class AudioManager {
    constructor() {
        this.sounds = {};
        this.music = null;
        this.musicVolume = 0.5;
        this.sfxVolume = 0.7;
        this.enabled = true;
        
        this.loadSounds();
    }
    
    async loadSounds() {
        const soundFiles = {
            shoot: 'assets/audio/laser.mp3',
            explosion: 'assets/audio/explosion.mp3',
            hit: 'assets/audio/hit.mp3',
            powerup: 'assets/audio/powerup.mp3',
            gameOver: 'assets/audio/gameover.mp3',
            background: 'assets/audio/background.mp3'
        };
        
        for (const [name, path] of Object.entries(soundFiles)) {
            try {
                const audio = new Audio();
                audio.src = path;
                audio.preload = 'auto';
                this.sounds[name] = audio;
                
                // بارگذاری صدا
                await new Promise((resolve, reject) => {
                    audio.addEventListener('canplaythrough', resolve);
                    audio.addEventListener('error', reject);
                });
            } catch (error) {
                console.warn(`Failed to load sound: ${name}`, error);
            }
        }
        
        console.log('Audio Manager Initialized');
    }
    
    playSound(name, volume = 1, loop = false) {
        if (!this.enabled || !this.sounds[name]) return;
        
        const sound = this.sounds[name].cloneNode();
        sound.volume = volume * this.sfxVolume;
        sound.loop = loop;
        
        sound.play().catch(e => {
            console.warn('Audio play failed:', e);
        });
        
        return sound;
    }
    
    playMusic(name, volume = 1) {
        if (!this.enabled) return;
        
        this.stopMusic();
        
        if (this.sounds[name]) {
            this.music = this.sounds[name].cloneNode();
            this.music.volume = volume * this.musicVolume;
            this.music.loop = true;
            
            this.music.play().catch(e => {
                console.warn('Music play failed:', e);
            });
        }
    }
    
    stopMusic() {
        if (this.music) {
            this.music.pause();
            this.music.currentTime = 0;
            this.music = null;
        }
    }
    
    setMusicVolume(volume) {
        this.musicVolume = Math.max(0, Math.min(1, volume));
        if (this.music) {
            this.music.volume = this.musicVolume;
        }
    }
    
    setSfxVolume(volume) {
        this.sfxVolume = Math.max(0, Math.min(1, volume));
    }
    
    toggleMute() {
        this.enabled = !this.enabled;
        if (!this.enabled) {
            this.stopMusic();
        }
        return this.enabled;
    }
}
