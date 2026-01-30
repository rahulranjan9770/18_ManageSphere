/**
 * Cloud Storage Integration Manager
 * Handles connections to Google Drive, OneDrive, AWS S3, and Dropbox
 */

class CloudStorageManager {
    constructor() {
        this.providers = {
            google_drive: {
                name: 'Google Drive',
                icon: '📁',
                color: '#4285f4',
                connected: false,
                authFields: ['access_token', 'api_key', 'api_secret']
            },
            onedrive: {
                name: 'OneDrive',
                icon: '☁️',
                color: '#0078d4',
                connected: false,
                authFields: ['access_token']
            },
            aws_s3: {
                name: 'AWS S3',
                icon: '🪣',
                color: '#ff9900',
                connected: false,
                authFields: ['aws_access_key_id', 'aws_secret_access_key', 'aws_region', 's3_bucket']
            },
            dropbox: {
                name: 'Dropbox',
                icon: '📦',
                color: '#0061ff',
                connected: false,
                authFields: ['access_token']
            }
        };

        this.currentProvider = null;
        this.currentFolder = null;
        this.selectedFiles = new Set();
        this.fileCache = new Map();

        this.init();
    }

    async init() {
        await this.loadConnectedProviders();
        this.renderProviderCards();
        this.setupEventListeners();
    }

    async loadConnectedProviders() {
        try {
            const response = await fetch('/cloud/providers');
            const data = await response.json();

            if (data.connected) {
                data.connected.forEach(provider => {
                    if (this.providers[provider]) {
                        this.providers[provider].connected = true;
                    }
                });
            }
        } catch (error) {
            console.error('Failed to load cloud providers:', error);
        }
    }

    renderProviderCards() {
        const container = document.getElementById('cloudProviders');
        if (!container) return;

        container.innerHTML = Object.entries(this.providers).map(([key, provider]) => `
            <div class="provider-card ${provider.connected ? 'connected' : ''}" 
                 data-provider="${key}">
                <div class="provider-icon">${provider.icon}</div>
                <div class="provider-name">${provider.name}</div>
                <div class="provider-status">
                    <span class="status-dot"></span>
                    <span>${provider.connected ? 'Connected' : 'Not connected'}</span>
                </div>
                <button class="connect-btn">
                    ${provider.connected ? 'Disconnect' : 'Connect'}
                </button>
            </div>
        `).join('');

        // Add click handlers
        container.querySelectorAll('.provider-card').forEach(card => {
            const provider = card.dataset.provider;

            card.querySelector('.connect-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.providers[provider].connected) {
                    this.disconnectProvider(provider);
                } else {
                    this.showConnectModal(provider);
                }
            });

            card.addEventListener('click', () => {
                if (this.providers[provider].connected) {
                    this.openFileBrowser(provider);
                }
            });
        });
    }

    showConnectModal(provider) {
        const modal = document.getElementById('cloudConnectModal');
        const providerInfo = this.providers[provider];

        if (!modal || !providerInfo) return;

        // Update modal title
        modal.querySelector('.modal-provider-name').textContent = providerInfo.name;
        modal.querySelector('.modal-provider-icon').textContent = providerInfo.icon;

        // Generate form fields
        const formContainer = modal.querySelector('.modal-form-fields');
        formContainer.innerHTML = this.generateFormFields(provider);

        // Store current provider
        modal.dataset.provider = provider;

        // Show modal
        modal.classList.add('active');
    }

    generateFormFields(provider) {
        const fields = {
            google_drive: `
                <div class="form-group">
                    <label>Access Token</label>
                    <input type="text" name="access_token" placeholder="Enter your access token">
                    <div class="help-text">
                        Get from <a href="https://console.developers.google.com/" target="_blank">Google Cloud Console</a>
                    </div>
                </div>
                <div class="form-group">
                    <label>API Key (Client ID)</label>
                    <input type="text" name="api_key" placeholder="Client ID">
                </div>
                <div class="form-group">
                    <label>API Secret (Client Secret)</label>
                    <input type="password" name="api_secret" placeholder="Client Secret">
                </div>
            `,
            onedrive: `
                <div class="form-group">
                    <label>Access Token</label>
                    <input type="text" name="access_token" placeholder="Enter your access token">
                    <div class="help-text">
                        Get from <a href="https://portal.azure.com/" target="_blank">Azure Portal</a>
                    </div>
                </div>
            `,
            aws_s3: `
                <div class="form-group">
                    <label>AWS Access Key ID</label>
                    <input type="text" name="aws_access_key_id" placeholder="AKIAIOSFODNN7EXAMPLE">
                </div>
                <div class="form-group">
                    <label>AWS Secret Access Key</label>
                    <input type="password" name="aws_secret_access_key" placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY">
                </div>
                <div class="form-group">
                    <label>AWS Region</label>
                    <input type="text" name="aws_region" placeholder="us-east-1" value="us-east-1">
                </div>
                <div class="form-group">
                    <label>S3 Bucket Name</label>
                    <input type="text" name="s3_bucket" placeholder="my-bucket-name">
                </div>
                <div class="help-text">
                    Get credentials from <a href="https://console.aws.amazon.com/iam/" target="_blank">AWS IAM Console</a>
                </div>
            `,
            dropbox: `
                <div class="form-group">
                    <label>Access Token</label>
                    <input type="text" name="access_token" placeholder="Enter your access token">
                    <div class="help-text">
                        Get from <a href="https://www.dropbox.com/developers/apps" target="_blank">Dropbox App Console</a>
                    </div>
                </div>
            `
        };

        const form = fields[provider] || '';
        return `
            ${form}
            <div class="demo-mode-section" style="margin-top: 15px; padding-top: 15px; border-top: 1px dashed #eee;">
                <button type="button" class="demo-btn" style="width: 100%; background: #f0f0f0; color: #666; border: 1px solid #ddd; padding: 8px; border-radius: 6px; cursor: pointer; font-size: 0.9em;">
                    🧪 Try Demo Mode (No credentials required)
                </button>
            </div>
        `;
    }

    async connectProvider(provider, credentials) {
        const modal = document.getElementById('cloudConnectModal');
        const connectBtn = modal.querySelector('.connect-btn');

        try {
            connectBtn.disabled = true;
            connectBtn.textContent = 'Connecting...';

            const params = new URLSearchParams({ provider, ...credentials });
            const response = await fetch(`/cloud/connect?${params}`, {
                method: 'POST'
            });

            const data = await response.json();

            if (response.ok && data.success) {
                this.providers[provider].connected = true;
                this.renderProviderCards();
                this.hideConnectModal();
                this.showToast(`✅ Connected to ${this.providers[provider].name}`, 'success');

                // Auto-open file browser
                this.openFileBrowser(provider);
            } else {
                this.showToast(`❌ ${data.detail || 'Connection failed'}`, 'error');
            }
        } catch (error) {
            console.error('Connect error:', error);
            this.showToast('❌ Connection failed. Please check your credentials.', 'error');
        } finally {
            connectBtn.disabled = false;
            connectBtn.textContent = 'Connect';
        }
    }

    async disconnectProvider(provider) {
        if (!confirm(`Disconnect from ${this.providers[provider].name}?`)) {
            return;
        }

        try {
            const params = new URLSearchParams({ provider });
            const response = await fetch(`/cloud/disconnect?${params}`, {
                method: 'POST'
            });

            if (response.ok) {
                this.providers[provider].connected = false;
                this.renderProviderCards();
                this.closeFileBrowser();
                this.showToast(`✅ Disconnected from ${this.providers[provider].name}`, 'success');
            }
        } catch (error) {
            console.error('Disconnect error:', error);
            this.showToast('❌ Disconnect failed', 'error');
        }
    }

    async openFileBrowser(provider, folderId = null) {
        this.currentProvider = provider;
        this.currentFolder = folderId;
        this.selectedFiles.clear();

        const browser = document.getElementById('cloudFileBrowser');
        if (!browser) return;

        browser.classList.add('active');

        // Update header
        const providerInfo = this.providers[provider];
        browser.querySelector('.browser-provider-name').textContent = providerInfo.name;
        browser.querySelector('.browser-provider-icon').textContent = providerInfo.icon;

        // Show loading
        this.showBrowserLoading();

        // Fetch files
        await this.loadFiles(provider, folderId);
    }

    async loadFiles(provider, folderId = null) {
        try {
            let url = `/cloud/${provider}/files`;
            if (folderId) {
                url += `?folder_id=${encodeURIComponent(folderId)}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            if (response.ok) {
                this.renderFileList(data.files);
            } else {
                this.showBrowserError(data.detail || 'Failed to load files');
            }
        } catch (error) {
            console.error('Load files error:', error);
            this.showBrowserError('Failed to load files');
        }
    }

    renderFileList(files) {
        const listContainer = document.getElementById('cloudFileList');
        if (!listContainer) return;

        if (files.length === 0) {
            listContainer.innerHTML = `
                <div class="cloud-empty">
                    <div class="empty-icon">📂</div>
                    <p>No files found in this location</p>
                </div>
            `;
            return;
        }

        // Sort: folders first, then files by name
        files.sort((a, b) => {
            if (a.is_folder && !b.is_folder) return -1;
            if (!a.is_folder && b.is_folder) return 1;
            return a.name.localeCompare(b.name);
        });

        listContainer.innerHTML = files.map(file => `
            <div class="cloud-file-item ${file.is_folder ? 'folder' : ''}" 
                 data-file-id="${file.id}"
                 data-file-name="${file.name}"
                 data-is-folder="${file.is_folder}">
                ${file.is_folder ? '' : `
                    <div class="file-checkbox">
                        <input type="checkbox" ${this.selectedFiles.has(file.id) ? 'checked' : ''}>
                    </div>
                `}
                <div class="file-icon">${this.getFileIcon(file)}</div>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-meta">
                        <span>${this.formatFileSize(file.size)}</span>
                        <span>${this.formatDate(file.modified_at)}</span>
                    </div>
                </div>
                <div class="file-actions">
                    ${file.is_folder ? `
                        <button class="open-folder-btn" title="Open folder">📂 Open</button>
                    ` : `
                        <button class="import-btn" title="Import this file">📥 Import</button>
                    `}
                </div>
            </div>
        `).join('');

        // Add event listeners
        this.setupFileListeners();
    }

    setupFileListeners() {
        const listContainer = document.getElementById('cloudFileList');
        if (!listContainer) return;

        listContainer.querySelectorAll('.cloud-file-item').forEach(item => {
            const fileId = item.dataset.fileId;
            const isFolder = item.dataset.isFolder === 'true';

            // Checkbox
            const checkbox = item.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.addEventListener('change', () => {
                    if (checkbox.checked) {
                        this.selectedFiles.add(fileId);
                        item.classList.add('selected');
                    } else {
                        this.selectedFiles.delete(fileId);
                        item.classList.remove('selected');
                    }
                    this.updateBulkActions();
                });
            }

            // Folder navigation
            if (isFolder) {
                // Double click anywhere
                item.addEventListener('dblclick', () => {
                    this.openFileBrowser(this.currentProvider, fileId);
                });

                // Single click on name/icon opens it too (more intuitive)
                item.querySelector('.file-info')?.addEventListener('click', (e) => {
                    e.stopPropagation(); // Prevent row selection if we want just navigation
                    this.openFileBrowser(this.currentProvider, fileId);
                });

                item.querySelector('.file-icon')?.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.openFileBrowser(this.currentProvider, fileId);
                });

                // Button
                item.querySelector('.open-folder-btn')?.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.openFileBrowser(this.currentProvider, fileId);
                });
            }

            // Import button
            item.querySelector('.import-btn')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.importFile(fileId, item.dataset.fileName);
            });
        });
    }

    updateBulkActions() {
        const bulkBar = document.getElementById('bulkActionsBar');
        const selectionCount = document.getElementById('selectionCount');

        if (!bulkBar) return;

        if (this.selectedFiles.size > 0) {
            bulkBar.classList.add('active');
            selectionCount.textContent = this.selectedFiles.size;
        } else {
            bulkBar.classList.remove('active');
        }
    }

    async importFile(fileId, fileName) {
        const btn = document.querySelector(`[data-file-id="${fileId}"] .import-btn`);
        if (btn) {
            btn.disabled = true;
            btn.textContent = '⏳ Importing...';
        }

        try {
            const params = new URLSearchParams({
                file_id: fileId,
                auto_index: 'true'
            });

            const response = await fetch(`/cloud/${this.currentProvider}/import?${params}`, {
                method: 'POST'
            });

            const data = await response.json();

            if (response.ok && data.success) {
                this.showToast(`✅ Imported: ${fileName}`, 'success');
                if (btn) {
                    btn.textContent = '✓ Imported';
                    btn.style.background = '#10b981';
                }

                // Update stats
                this.updateStats();
            } else {
                this.showToast(`❌ Failed to import: ${data.detail || 'Unknown error'}`, 'error');
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = '📥 Import';
                }
            }
        } catch (error) {
            console.error('Import error:', error);
            this.showToast('❌ Import failed', 'error');
            if (btn) {
                btn.disabled = false;
                btn.textContent = '📥 Import';
            }
        }
    }

    async importSelectedFiles() {
        if (this.selectedFiles.size === 0) return;

        const fileIds = Array.from(this.selectedFiles);
        const progressEl = document.getElementById('importProgress');
        const progressFill = progressEl?.querySelector('.progress-fill');
        const progressStatus = progressEl?.querySelector('.import-progress-status');

        // Show progress
        if (progressEl) {
            progressEl.classList.add('active');
            progressFill.style.width = '0%';
            progressStatus.textContent = `Importing 0 of ${fileIds.length}...`;
        }

        try {
            const response = await fetch(`/cloud/${this.currentProvider}/import-batch?auto_index=true`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_ids: fileIds })
            });

            const data = await response.json();

            if (response.ok) {
                // Update progress
                if (progressEl) {
                    progressFill.style.width = '100%';
                    progressStatus.textContent = `Imported ${data.successful} of ${data.total} files`;

                    setTimeout(() => {
                        progressEl.classList.remove('active');
                    }, 3000);
                }

                this.showToast(`✅ Imported ${data.successful} files`, 'success');
                this.selectedFiles.clear();
                this.updateBulkActions();
                this.loadFiles(this.currentProvider, this.currentFolder);
                this.updateStats();
            }
        } catch (error) {
            console.error('Batch import error:', error);
            this.showToast('❌ Batch import failed', 'error');
            if (progressEl) {
                progressEl.classList.remove('active');
            }
        }
    }

    async searchFiles(query) {
        if (!query || !this.currentProvider) return;

        this.showBrowserLoading();

        try {
            const response = await fetch(`/cloud/${this.currentProvider}/search?query=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (response.ok) {
                this.renderFileList(data.files);
            }
        } catch (error) {
            console.error('Search error:', error);
            this.showBrowserError('Search failed');
        }
    }

    showBrowserLoading() {
        const listContainer = document.getElementById('cloudFileList');
        if (!listContainer) return;

        listContainer.innerHTML = `
            <div class="cloud-loading">
                <div class="loading-spinner"></div>
                <p>Loading files...</p>
            </div>
        `;
    }

    showBrowserError(message) {
        const listContainer = document.getElementById('cloudFileList');
        if (!listContainer) return;

        listContainer.innerHTML = `
            <div class="cloud-empty">
                <div class="empty-icon">⚠️</div>
                <p>${message}</p>
            </div>
        `;
    }

    closeFileBrowser() {
        const browser = document.getElementById('cloudFileBrowser');
        if (browser) {
            browser.classList.remove('active');
        }
        this.currentProvider = null;
        this.currentFolder = null;
        this.selectedFiles.clear();
    }

    hideConnectModal() {
        const modal = document.getElementById('cloudConnectModal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    setupEventListeners() {
        // Connect modal form
        const modal = document.getElementById('cloudConnectModal');
        if (modal) {
            modal.querySelector('.cloud-modal-close')?.addEventListener('click', () => {
                this.hideConnectModal();
            });

            modal.querySelector('.cancel-btn')?.addEventListener('click', () => {
                this.hideConnectModal();
            });

            modal.querySelector('.connect-btn')?.addEventListener('click', () => {
                const provider = modal.dataset.provider;
                const credentials = {};

                modal.querySelectorAll('.modal-form-fields input').forEach(input => {
                    if (input.value) {
                        credentials[input.name] = input.value;
                    }
                });

                this.connectProvider(provider, credentials);
            });

            // Demo Mode Button
            modal.addEventListener('click', (e) => {
                if (e.target.closest('.demo-btn')) {
                    const inputs = modal.querySelectorAll('.modal-form-fields input');
                    inputs.forEach(input => input.value = 'demo');
                    // Trigger connect
                    modal.querySelector('.connect-btn').click();
                }
            });

            // Close on backdrop click
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideConnectModal();
                }
            });
        }

        // File browser close
        document.getElementById('closeBrowserBtn')?.addEventListener('click', () => {
            this.closeFileBrowser();
        });

        // Search
        const searchInput = document.getElementById('cloudSearchInput');
        let searchTimeout;
        searchInput?.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const query = searchInput.value.trim();
                if (query.length >= 2) {
                    this.searchFiles(query);
                } else if (query.length === 0) {
                    this.loadFiles(this.currentProvider, this.currentFolder);
                }
            }, 300);
        });

        // Bulk actions
        document.getElementById('importSelectedBtn')?.addEventListener('click', () => {
            this.importSelectedFiles();
        });

        document.getElementById('clearSelectionBtn')?.addEventListener('click', () => {
            this.selectedFiles.clear();
            document.querySelectorAll('.cloud-file-item').forEach(item => {
                item.classList.remove('selected');
                const checkbox = item.querySelector('input[type="checkbox"]');
                if (checkbox) checkbox.checked = false;
            });
            this.updateBulkActions();
        });

        // Back to root
        document.getElementById('backToRootBtn')?.addEventListener('click', () => {
            this.openFileBrowser(this.currentProvider, null);
        });

        // Refresh
        document.getElementById('refreshFilesBtn')?.addEventListener('click', () => {
            this.loadFiles(this.currentProvider, this.currentFolder);
        });
    }

    // Utility methods
    getFileIcon(file) {
        if (file.is_folder) return '📁';

        const ext = file.name.split('.').pop()?.toLowerCase();
        const icons = {
            pdf: '📕',
            doc: '📘', docx: '📘',
            txt: '📄',
            jpg: '🖼️', jpeg: '🖼️', png: '🖼️', gif: '🖼️', bmp: '🖼️',
            mp3: '🎵', wav: '🎵', m4a: '🎵',
            mp4: '🎬', avi: '🎬', mov: '🎬',
            zip: '📦', rar: '📦',
            xls: '📊', xlsx: '📊', csv: '📊',
            ppt: '📈', pptx: '📈'
        };

        return icons[ext] || '📄';
    }

    formatFileSize(bytes) {
        if (!bytes) return '-';
        const units = ['B', 'KB', 'MB', 'GB'];
        let i = 0;
        while (bytes >= 1024 && i < units.length - 1) {
            bytes /= 1024;
            i++;
        }
        return `${bytes.toFixed(1)} ${units[i]}`;
    }

    formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    }

    showToast(message, type = 'info') {
        // Use existing toast system if available
        if (window.pwaManager && window.pwaManager.showToast) {
            window.pwaManager.showToast(message, type);
            return;
        }

        // Create simple toast
        const toast = document.createElement('div');
        toast.className = `cloud-toast cloud-toast-${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => toast.classList.add('show'), 10);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    async updateStats() {
        try {
            const response = await fetch('/stats');
            const stats = await response.json();

            const chunksEl = document.getElementById('totalChunks');
            if (chunksEl) {
                chunksEl.textContent = stats.total_chunks;
            }
        } catch (error) {
            console.error('Stats update error:', error);
        }
    }
}

// Initialize on DOM ready
let cloudStorageManager;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        cloudStorageManager = new CloudStorageManager();
    });
} else {
    cloudStorageManager = new CloudStorageManager();
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CloudStorageManager;
}
