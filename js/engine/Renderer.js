class Renderer {
    constructor(ctx) {
        this.ctx = ctx;
        this.particleSystems = [];
        this.lights = [];
        this.postProcessing = {
            bloom: true,
            motionBlur: true,
            colorGrading: true
        };
    }
    
    // رندر اسپرایت با افکت‌های پیشرفته
    drawSprite(sprite, x, y, width, height, rotation = 0, alpha = 1) {
        this.ctx.save();
        this.ctx.translate(x + width/2, y + height/2);
        this.ctx.rotate(rotation);
        this.ctx.globalAlpha = alpha;
        
        // اعمال افکت‌های بصری
        if (this.postProcessing.bloom) {
            this.applyBloomEffect(sprite, width, height);
        }
        
        this.ctx.drawImage(sprite, -width/2, -height/2, width, height);
        this.ctx.restore();
    }
    
    // افکت Bloom
    applyBloomEffect(sprite, width, height) {
        // پیاده‌سازی افکت Bloom برای نورهای درخشان
        this.ctx.shadowColor = 'rgba(255, 255, 255, 0.3)';
        this.ctx.shadowBlur = 15;
        this.ctx.shadowOffsetX = 0;
        this.ctx.shadowOffsetY = 0;
    }
    
    // رندر ذرات
    drawParticle(particle) {
        this.ctx.save();
        this.ctx.globalAlpha = particle.alpha;
        this.ctx.fillStyle = particle.color;
        
        // افکت نور برای ذرات
        if (particle.light) {
            const gradient = this.ctx.createRadialGradient(
                particle.x, particle.y, 0,
                particle.x, particle.y, particle.radius * 2
            );
            gradient.addColorStop(0, particle.color);
            gradient.addColorStop(1, 'transparent');
            this.ctx.fillStyle = gradient;
        }
        
        this.ctx.beginPath();
        this.ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.restore();
    }
    
    // رندر متن با سایه و افکت
    drawText(text, x, y, size, color = '#ffffff', align = 'center') {
        this.ctx.save();
        this.ctx.font = `bold ${size}px Arial`;
        this.ctx.textAlign = align;
        this.ctx.textBaseline = 'middle';
        
        // سایه متن
        this.ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
        this.ctx.shadowBlur = 4;
        this.ctx.shadowOffsetX = 2;
        this.ctx.shadowOffsetY = 2;
        
        this.ctx.fillStyle = color;
        this.ctx.fillText(text, x, y);
        this.ctx.restore();
    }
    
    // رندر نوار سلامتی
    drawHealthBar(x, y, width, height, current, max, color = '#4caf50') {
        const fillWidth = (current / max) * width;
        
        // پس‌زمینه نوار
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        this.ctx.fillRect(x, y, width, height);
        
        // نوار سلامتی
        const gradient = this.ctx.createLinearGradient(x, y, x + fillWidth, y);
        gradient.addColorStop(0, color);
        gradient.addColorStop(1, '#8bc34a');
        
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(x, y, fillWidth, height);
        
        // حاشیه
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x, y, width, height);
    }
    
    // ایجاد افکت انفجار
    createExplosion(x, y, radius, color = '#ff6b00') {
        const particles = [];
        const particleCount = 50;
        
        for (let i = 0; i < particleCount; i++) {
            particles.push({
                x: x,
                y: y,
                vx: (Math.random() - 0.5) * 10,
                vy: (Math.random() - 0.5) * 10,
                radius: Math.random() * 3 + 1,
                color: color,
                alpha: 1,
                life: 1,
                decay: 0.02 + Math.random() * 0.02
            });
        }
        
        this.particleSystems.push({
            particles: particles,
            update: function(deltaTime) {
                for (let i = this.particles.length - 1; i >= 0; i--) {
                    const p = this.particles[i];
                    
                    p.x += p.vx;
                    p.y += p.vy;
                    p.vy += 0.1; // گرانش
                    p.life -= p.decay;
                    p.alpha = p.life;
                    
                    if (p.life <= 0) {
                        this.particles.splice(i, 1);
                    }
                }
                
                return this.particles.length > 0;
            }
        });
    }
    
    // به روز رسانی سیستم ذرات
    updateParticles(deltaTime) {
        for (let i = this.particleSystems.length - 1; i >= 0; i--) {
            const system = this.particleSystems[i];
            if (!system.update(deltaTime)) {
                this.particleSystems.splice(i, 1);
            }
        }
    }
    
    // رندر تمام ذرات
    renderParticles() {
        this.particleSystems.forEach(system => {
            system.particles.forEach(particle => {
                this.drawParticle(particle);
            });
        });
    }
                              }
