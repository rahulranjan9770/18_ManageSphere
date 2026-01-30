// PWA Installation & Service Worker Registration
class PWAManager {
    constructor() {
        this.deferredPrompt = null;
        this.isInstalled = false;
        this.isOnline = navigator.onLine;
        this.swRegistration = null;
        this.init();
    }

    async init() {
        this.checkInstallation();
        this.registerServiceWorker();
        this.setupInstallPrompt();
        this.setupOnlineOfflineHandlers();
        this.setupUpdateNotification();
    }

    // Check if app is already installed
    checkInstallation() {
        // Check if running as PWA
        const isStandalone = window.matchMedia('(display-mode: standalone)').matches ||
            window.navigator.standalone ||
            document.referrer.includes('android-app://');

        this.isInstalled = isStandalone;

        if (this.isInstalled) {
            console.log('[PWA] App is running in standalone mode');
            this.hideInstallButton();
        }
    }

    // Register service worker
    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                this.swRegistration = await navigator.serviceWorker.register('/static/sw.js', {
                    scope: '/'
                });

                console.log('[PWA] Service Worker registered:', this.swRegistration.scope);

                // Check for updates periodically
                setInterval(() => {
                    this.swRegistration.update();
                }, 60 * 60 * 1000); // Check every hour

                // Listen for service worker updates
                this.swRegistration.addEventListener('updatefound', () => {
                    const newWorker = this.swRegistration.installing;

                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            this.showUpdateNotification();
                        }
                    });
                });

            } catch (error) {
                console.error('[PWA] Service Worker registration failed:', error);
            }
        } else {
            console.log('[PWA] Service Workers not supported');
        }
    }

    // Setup install prompt
    setupInstallPrompt() {
        // Listen for beforeinstallprompt event
        window.addEventListener('beforeinstallprompt', (e) => {
            console.log('[PWA] Install prompt available');
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallButton();
        });

        // Listen for app installed event
        window.addEventListener('appinstalled', () => {
            console.log('[PWA] App installed successfully');
            this.isInstalled = true;
            this.hideInstallButton();
            this.showToast('✅ App installed successfully! You can now use it offline.', 'success');
            this.deferredPrompt = null;
        });
    }

    // Show install button
    showInstallButton() {
        let installButton = document.getElementById('pwaInstallBtn');

        if (!installButton) {
            // Create install button
            installButton = document.createElement('button');
            installButton.id = 'pwaInstallBtn';
            installButton.className = 'pwa-install-btn';
            installButton.innerHTML = `
        <span class="install-icon">📱</span>
        <span class="install-text">Install App</span>
      `;
            installButton.title = 'Install this app for offline access';

            // Add to header
            const header = document.querySelector('header');
            if (header) {
                header.appendChild(installButton);
            }

            // Add click handler
            installButton.addEventListener('click', () => this.promptInstall());
        }

        installButton.style.display = 'flex';
    }

    // Hide install button
    hideInstallButton() {
        const installButton = document.getElementById('pwaInstallBtn');
        if (installButton) {
            installButton.style.display = 'none';
        }
    }

    // Prompt user to install
    async promptInstall() {
        if (!this.deferredPrompt) {
            this.showToast('⚠️ Installation not available on this device/browser', 'warning');
            return;
        }

        // Show the install prompt
        this.deferredPrompt.prompt();

        // Wait for the user's response
        const { outcome } = await this.deferredPrompt.userChoice;

        console.log(`[PWA] User response to install prompt: ${outcome}`);

        if (outcome === 'accepted') {
            console.log('[PWA] User accepted the install prompt');
        } else {
            console.log('[PWA] User dismissed the install prompt');
            this.showToast('ℹ️ You can install the app later from the browser menu', 'info');
        }

        this.deferredPrompt = null;
    }

    // Setup online/offline handlers
    setupOnlineOfflineHandlers() {
        // Create offline indicator
        this.createOfflineIndicator();

        window.addEventListener('online', () => {
            console.log('[PWA] App is online');
            this.isOnline = true;
            this.updateOnlineStatus(true);
            this.showToast('✅ Back online! Syncing data...', 'success');
            this.syncWhenOnline();
        });

        window.addEventListener('offline', () => {
            console.log('[PWA] App is offline');
            this.isOnline = false;
            this.updateOnlineStatus(false);
            this.showToast('⚠️ You are offline. Some features may be limited.', 'warning');
        });

        // Set initial status
        this.updateOnlineStatus(this.isOnline);
    }

    // Create offline indicator
    createOfflineIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'pwaOnlineStatus';
        indicator.className = 'pwa-online-status';
        document.body.appendChild(indicator);
    }

    // Update online status UI
    updateOnlineStatus(isOnline) {
        const indicator = document.getElementById('pwaOnlineStatus');
        if (indicator) {
            indicator.className = `pwa-online-status ${isOnline ? 'online' : 'offline'}`;
            indicator.innerHTML = `
        <span class="status-dot"></span>
        <span class="status-text">${isOnline ? 'Online' : 'Offline'}</span>
      `;
        }
    }

    // Sync data when back online
    async syncWhenOnline() {
        if ('serviceWorker' in navigator && 'sync' in navigator.serviceWorker) {
            try {
                const registration = await navigator.serviceWorker.ready;
                await registration.sync.register('sync-uploads');
                console.log('[PWA] Background sync registered');
            } catch (error) {
                console.error('[PWA] Background sync registration failed:', error);
            }
        }
    }

    // Show update notification
    showUpdateNotification() {
        const notification = document.createElement('div');
        notification.className = 'pwa-update-notification';
        notification.innerHTML = `
      <div class="update-content">
        <span class="update-icon">🔄</span>
        <span class="update-text">A new version is available!</span>
        <button class="update-btn" id="pwaUpdateBtn">Update Now</button>
        <button class="dismiss-btn" id="pwaDismissBtn">Later</button>
      </div>
    `;

        document.body.appendChild(notification);

        // Update button handler
        document.getElementById('pwaUpdateBtn').addEventListener('click', () => {
            if (this.swRegistration && this.swRegistration.waiting) {
                this.swRegistration.waiting.postMessage({ type: 'SKIP_WAITING' });
                window.location.reload();
            }
        });

        // Dismiss button handler
        document.getElementById('pwaDismissBtn').addEventListener('click', () => {
            notification.remove();
        });

        // Auto-show
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
    }

    // Setup update notification listener
    setupUpdateNotification() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('controllerchange', () => {
                console.log('[PWA] Service Worker controller changed');
            });
        }
    }

    // Show toast notification
    showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `pwa-toast pwa-toast-${type}`;
        toast.textContent = message;

        document.body.appendChild(toast);

        // Show toast
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);

        // Auto-hide toast
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 4000);
    }

    // Clear all caches (for debugging)
    async clearAllCaches() {
        if ('caches' in window) {
            const cacheNames = await caches.keys();
            await Promise.all(cacheNames.map(name => caches.delete(name)));
            console.log('[PWA] All caches cleared');
            this.showToast('✅ All caches cleared', 'success');
        }
    }

    // Check if device is iOS
    isIOS() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    }

    // Show iOS install instructions
    showIOSInstructions() {
        if (this.isIOS() && !this.isInstalled) {
            const instructions = document.createElement('div');
            instructions.className = 'ios-install-instructions';
            instructions.innerHTML = `
        <div class="ios-install-content">
          <h3>Install on iOS</h3>
          <ol>
            <li>Tap the Share button <span style="font-size: 1.2em;">⎙</span></li>
            <li>Scroll down and tap "Add to Home Screen"</li>
            <li>Tap "Add" in the top-right corner</li>
          </ol>
          <button class="ios-close-btn" onclick="this.parentElement.parentElement.remove()">Got it!</button>
        </div>
      `;

            document.body.appendChild(instructions);

            setTimeout(() => {
                instructions.classList.add('show');
            }, 100);
        }
    }
}

// Initialize PWA Manager
let pwaManager;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        pwaManager = new PWAManager();
    });
} else {
    pwaManager = new PWAManager();
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PWAManager;
}
