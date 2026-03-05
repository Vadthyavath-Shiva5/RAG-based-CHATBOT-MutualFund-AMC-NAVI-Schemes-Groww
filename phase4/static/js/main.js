// Main page functionality
class App {
    constructor() {
        this.faqItems = document.querySelectorAll('.faq-item');
        this.actionButtons = document.querySelectorAll('.action-btn');
        this.navLinks = document.querySelectorAll('.nav-link');
        this.heroBtn = document.querySelector('.btn-primary');
        
        this.init();
    }

    init() {
        this.initFAQ();
        this.initActionButtons();
        this.initScrollTracking();
        this.initHeroButton();
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
        this.actionButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const query = btn.textContent.trim();
                this.triggerChat(query);
            });
        });
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

    // Initialize hero button
    initHeroButton() {
        if (this.heroBtn) {
            this.heroBtn.addEventListener('click', () => {
                this.triggerChat('What are mutual funds?');
            });
        }
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
    
    // Open chat
    if (typeof openChat === 'function') {
        openChat();
    }
    
    // Send the query after a short delay to ensure chat is open
    setTimeout(() => {
        const chatInput = document.getElementById('chatInput');
        const chatMessages = document.getElementById('chatMessages');
        
        if (chatInput && chatMessages) {
            // Remove intro menu if present
            const menus = chatMessages.querySelectorAll('.bot-menu');
            menus.forEach(m => {
                const parent = m.parentElement.parentElement;
                if (parent) parent.remove();
            });
            
            chatInput.value = query;
            chatInput.focus();
            
            // Trigger send
            const sendBtn = document.getElementById('sendBtn');
            if (sendBtn) {
                sendBtn.click();
            }
        }
    }, 400);
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