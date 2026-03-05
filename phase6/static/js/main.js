// Main page functionality
class App {
    constructor() {
        this.faqItems = document.querySelectorAll('.faq-item');
        this.actionButtons = document.querySelectorAll('.action-btn');
        this.navLinks = document.querySelectorAll('.nav-link');
        this.heroBtn = document.querySelector('.btn-primary');
        this.topFreshness = document.getElementById('topFreshness');
        this.chatFreshness = document.getElementById('chatFreshness');
        this.freshnessPollMs = 120000;
        
        this.init();
    }

    init() {
        this.initFAQ();
        this.initScrollTracking();
        this.initDataFreshness();
    }

    // Initialize FAQ Accordion
    initFAQ() {
        this.faqItems.forEach(item => {
            const question = item.querySelector('.faq-question');
            
            question.addEventListener('click', () => {
                // Close other items
                this.faqItems.forEach(otherItem => {
                    if (otherItem !== item) {
                        otherItem.classList.remove('active');
                    }
                });
                
                // Toggle current item
                item.classList.toggle('active');
            });
        });
    }

    // Initialize Quick Action Buttons
    initActionButtons() {
        // Quick question buttons are handled by inline askQuestion(query) in HTML.
    }

    // Trigger chat with predefined query
    triggerChat(query) {
        // Use global helper to open chat
        if (typeof openChat === 'function') {
            openChat();
        } else {
            const chatBox = document.getElementById('chatBox');
            const chatToggle = document.getElementById('chatToggle');
            if (!chatBox.classList.contains('active')) {
                chatBox.classList.add('active');
                chatToggle.classList.add('active');
            }
        }

        // Focus input and set text after chat opens
        setTimeout(() => {
            const chatInput = document.getElementById('chatInput');
            const chatMessages = document.getElementById('chatMessages');
            
            // Remove intro menu if present
            const menus = chatMessages.querySelectorAll('.bot-menu');
            menus.forEach(m => m.parentElement.parentElement.remove());
            
            chatInput.value = query;
            chatInput.focus();

            const sendBtn = document.getElementById('sendBtn');
            sendBtn.click();
        }, 300);
    }

    // Track scroll position and highlight active nav link
    initScrollTracking() {
        window.addEventListener('scroll', () => {
            let current = '';

            const sections = document.querySelectorAll('section, .hero');
            
            sections.forEach(section => {
                const sectionTop = section.offsetTop;
                const sectionHeight = section.clientHeight;
                
                if (window.pageYOffset >= sectionTop - 100) {
                    current = section.getAttribute('id');
                }
            });

            this.navLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href').includes(current)) {
                    link.classList.add('active');
                }
            });
        });
    }

    initDataFreshness() {
        this.refreshDataFreshness();
        window.setInterval(() => {
            this.refreshDataFreshness();
        }, this.freshnessPollMs);
    }

    async refreshDataFreshness() {
        const configuredBase = (window.BACKEND_API_BASE_URL || '').replace(/\/$/, '');
        const freshnessUrl = configuredBase ? `${configuredBase}/sources` : '/api/sources';

        try {
            const response = await fetch(freshnessUrl, { method: 'GET' });
            if (!response.ok) {
                throw new Error(`Freshness API failed (${response.status})`);
            }

            const payload = await response.json();
            const latestTimestamp = this.extractLatestTimestamp(payload);
            this.renderDataFreshness(latestTimestamp);
        } catch (error) {
            console.warn('Unable to refresh data freshness indicator:', error);
            this.renderDataFreshness(new Date());
        }
    }

    extractLatestTimestamp(payload) {
        const values = [];

        if (payload && payload.latest_data_timestamp) {
            values.push(payload.latest_data_timestamp);
        }
        if (payload && payload.latest_data_date) {
            values.push(payload.latest_data_date);
        }
        if (payload && payload.generated_at) {
            values.push(payload.generated_at);
        }

        if (payload && Array.isArray(payload.sources)) {
            payload.sources.forEach((source) => {
                if (!source) {
                    return;
                }
                values.push(source.last_updated || source.last_refreshed || source.fetched_at || '');
            });
        } else if (payload && payload.sources && typeof payload.sources === 'object') {
            Object.values(payload.sources).forEach((source) => {
                if (!source || typeof source !== 'object') {
                    return;
                }
                values.push(source.last_updated || source.last_refreshed || source.fetched_at || '');
            });
        }

        if (payload && typeof payload === 'object') {
            ['groww', 'amfi', 'sebi'].forEach((domainKey) => {
                const source = payload[domainKey];
                if (!source || typeof source !== 'object') {
                    return;
                }
                values.push(source.last_updated || source.last_refreshed || '');
            });
        }

        let latest = null;
        values.forEach((rawValue) => {
            if (!rawValue) {
                return;
            }
            const candidate = new Date(rawValue);
            if (Number.isNaN(candidate.getTime())) {
                return;
            }
            if (!latest || candidate > latest) {
                latest = candidate;
            }
        });

        return latest || new Date();
    }

    formatFreshnessLabel(dateValue) {
        if (!dateValue || Number.isNaN(dateValue.getTime())) {
            dateValue = new Date();
        }
        return dateValue.toLocaleString('en-IN', {
            year: 'numeric',
            month: 'short',
            day: '2-digit',
        });
    }

    renderDataFreshness(latestDate) {
        const rendered = this.formatFreshnessLabel(latestDate);
        if (this.topFreshness) {
            this.topFreshness.textContent = `Data updated: ${rendered}`;
        }
        if (this.chatFreshness) {
            this.chatFreshness.textContent = `Facts loaded till: ${rendered}`;
        }
    }

    // Initialize hero button
    initHeroButton() {
        // Hero button opens chat via inline openChat() in HTML.
    }

    // Smooth scroll to section
    scrollToSection(sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.scrollIntoView({ behavior: 'smooth' });
        }
    }
}

// Navbar Brand Click Handler
function initNavbarBrand() {
    const brand = document.querySelector('.navbar-brand');
    if (brand) {
        brand.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }
}

// Navigation Link Handlers
function initNavLinks() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const href = link.getAttribute('href');
            
            if (href.startsWith('#')) {
                const sectionId = href.substring(1);
                const section = document.getElementById(sectionId);
                if (section) {
                    section.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    });
}

// Page Load Animation
function initPageAnimation() {
    // Fade in on load
    document.body.style.opacity = '0';
    document.body.style.transition = 'opacity 0.5s ease';
    
    window.addEventListener('load', () => {
        document.body.style.opacity = '1';
    });

    // Intersection Observer for reveal animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observe cards and sections
    const elements = document.querySelectorAll('.info-card, .action-btn, .faq-item');
    elements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(el);
    });
}

// Global helper for quick action buttons
window.askQuestion = function(query) {
    console.log('askQuestion called with:', query);

    if (typeof sendChatMessage === 'function') {
        sendChatMessage(query);
        return;
    }

    // Fallback if chat widget has not initialized yet.
    if (typeof openChat === 'function') {
        openChat();
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize main app
    new App();
    
    // Initialize additional features
    initNavbarBrand();
    initNavLinks();
    initPageAnimation();

    console.log('Page initialized successfully');
});
