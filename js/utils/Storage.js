class Storage {
    static set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('Storage set error:', error);
            return false;
        }
    }
    
    static get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Storage get error:', error);
            return defaultValue;
        }
    }
    
    static remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('Storage remove error:', error);
            return false;
        }
    }
    
    static clear() {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.error('Storage clear error:', error);
            return false;
        }
    }
    
    static has(key) {
        return localStorage.getItem(key) !== null;
    }
    
    static getKeys() {
        const keys = [];
        for (let i = 0; i < localStorage.length; i++) {
            keys.push(localStorage.key(i));
        }
        return keys;
    }
    
    static getSize() {
        let size = 0;
        for (let key in localStorage) {
            if (localStorage.hasOwnProperty(key)) {
                size += localStorage[key].length;
            }
        }
        return size;
    }
    
    // متدهای مخصوص بازی
    static saveGame(data) {
        return this.set('galacticWarfare_save', data);
    }
    
    static loadGame() {
        return this.get('galacticWarfare_save');
    }
    
    static saveHighScore(score) {
        return this.set('galacticWarfare_highscore', score);
    }
    
    static loadHighScore() {
        return this.get('galacticWarfare_highscore', 0);
    }
    
    static saveSettings(settings) {
        return this.set('galacticWarfare_settings', settings);
    }
    
    static loadSettings() {
        return this.get('galacticWarfare_settings', {
            musicVolume: 0.5,
            sfxVolume: 0.7,
            controls: 'touch'
        });
    }
}
