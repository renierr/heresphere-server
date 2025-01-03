function localStoreSettingsLoading() {
    const defaults = { cardLayout: true, pageSize: 12, filterAccordionOpen: true };
    let storedSetting = JSON.parse(localStorage.getItem('settings')) || {};
    storedSetting = Object.assign({}, defaults, storedSetting);
    return storedSetting;
}

// common.js
export const data = {
    files: [],
    filter: '',
    videoUrl: '',
    selectedFolder: '',
    loading: false,
    currentSort: 'created',
    currentSortDir: 'desc',
    serverOutput: '',
    serverResult: null,
    currentThumbnail: null,
    currentPage: 1,
    totalItems: 0,
    totalSize: 0,
    confirmData: {},
    settings: localStoreSettingsLoading(),
};

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        const later = () => {
            timeout = null;
        };
        const callNow = !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
}

export const methods = {
    formatDate(epochSeconds) {
        if (epochSeconds < 1) {
            return '';
        }
        const date = new Date(epochSeconds * 1000);
        const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' };
        return date.toLocaleDateString(undefined, options);
    },
    formatFileSize(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        if (bytes === 0) return '0 Byte';
        const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
        return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i];
    },
    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    },
    openThumbnail(thumbnail) {
        this.currentThumbnail = thumbnail;
        const modal = new bootstrap.Modal(document.getElementById('thumbnailModal'));
        modal.show();
    },
    changePage(page) {
        if (page < 1) {
            this.currentPage = 1;
        } else if (page > this.totalPages) {
            this.currentPage = this.totalPages;
        } else {
            this.currentPage = page;
        }
    },
    generateThumbnail(file) {
        fetch('/api/generate_thumbnail', {
            method: 'POST',
            body: JSON.stringify({ video_path: file }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(data => {
                this.serverResult = data.success ? data : 'Failed to generate thumbnail';
            })
            .catch(error => {
                console.error('Error generating thumbnail:', error);
                this.serverResult = 'Error generating thumbnails';
            });

    },
    fetchFiles: debounce(function () {
            console.log('Fetching files');
            // if we are in library url path we should use library api
            const library = window.location.pathname.includes('/library');

            this.loading = true;
            const url = library ? '/api/library/list' : '/api/list';
            fetch(url)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    this.files = data;
                    this.loading = false;
                })
                .catch(error => {
                    console.error('There was an error fetching the files:', error);
                    this.loading = false;
                })
        }, 3000),
    generateThumbnails() {
        // if we are in library url path we should use library api
        const library = window.location.pathname.includes('/library');
        const url = library ? '/api/library/generate_thumbnails' : '/api/generate_thumbnails';
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(data => {
                this.serverResult = data.success ? data : 'Failed to generate thumbnails';
            })
            .catch(error => {
                console.error('Error generating thumbnails:', error);
                this.serverResult = 'Error generating thumbnails';
            });
    },
    confirmCleanup() {
        this.confirmData = {
            title: 'Cleanup files',
            message: `This will clean the download tracked files and find orphan thumbnails and delete them, Are you sure you want to proceed?`,
            submit: 'Cleanup',
            action: this.cleanup,
        }
        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
        modal.show();
    },
    cleanup() { // Add this method
        fetch('/cleanup')
            .then(response => response.json())
            .then(data => {
                this.serverResult = data;
                this.fetchFiles();
            })
            .catch(error => {
                console.error('Error:', error);
                this.serverResult = 'Error occurred during cleanup';
            });
    },
    cacheClear: function () {
        fetch('/cache/clear')
            .then(response => response.json())
            .then(data => {
                this.serverResult = data;
                this.fetchFiles();
            })
            .catch(error => {
                console.error('Error:', error);
                this.serverResult = 'Error clearing cache';
            });
    },
    showMessage: function (input) {
        const toastElement = document.getElementById('serverResultToast');
        const toastMessage = document.getElementById('serverResultMessage');
        let message;
        try {
            if (input !== null && typeof input === 'object') {
                message = input.message || JSON.stringify(input);
            } else {
                message = input;
            }
        } catch (e) {
            message = input;
        }
        toastMessage.textContent = message;
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
    },
    confirmDeleteFile(filename) {
        this.confirmData = {
            title: 'Delete file',
            message: `Are you sure you want to delete the following file?`,
            file: filename,
            submit: 'Delete',
            action: this.deleteFile,
        }
        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
        modal.show();
    },
    deleteFile(confData) {
        if (!confData && !confData.file) {
            this.showMessage('Wrong number of parameters for deleteFile');
            return;
        }
        const file = confData.file;
        const utf8Bytes = new TextEncoder().encode(file);
        const encodedUrl = btoa(String.fromCharCode(...utf8Bytes));
        this.confirmData = {};
        fetch(`/api/files?url=${encodeURIComponent(encodedUrl)}`, {
            method: 'DELETE',
        })
            .then(response => response.json())
            .then((data) => {
                this.serverResult = data;
                this.fetchFiles();
            })
            .catch(error => {
                console.error('Error deleting bookmark:', error);
            });
    },
    playVideo(filename) {
        const videoModalBody = document.getElementById('videoModalBody');
        videoModalBody.innerHTML = `
            <video-js id="videoPlayer" class="vjs-default-skin w-100" controls autoplay>
                <source src="${filename}" type="video/mp4">
            </video-js>
        `;
        videojs('videoPlayer');
        const videoModal = new bootstrap.Modal(document.getElementById('videoModal'));
        videoModal.show();
    },
    saveSettings() {
        localStorage.setItem('settings', JSON.stringify(this.settings));
    },
    handleKeyup(event) {
        // only if paging present
        if (this.totalPages === 1) return;

        if (event.key === 'ArrowLeft') {
            this.changePage(this.currentPage - 1);
        } else if (event.key === 'ArrowRight') {
            this.changePage(this.currentPage + 1);
        }
    },
    toggleAccordion() {
        this.settings.filterAccordionOpen = !this.settings.filterAccordionOpen;
        this.saveSettings();
    },
};

export const computed = {
    filteredFiles: function () {

        let filtered = this.files;
        if (this.selectedFolder) {
            filtered = this.files.filter(file => file.folder === this.selectedFolder);
        }

        filtered = filtered.filter(file => {
            return file.filename.toLowerCase().includes(this.filter.toLowerCase());
        });

        filtered = filtered.sort((a, b) => {
            let modifier = 1;
            if (this.currentSortDir === 'desc') modifier = -1;
            if (a[this.currentSort] < b[this.currentSort]) return -1 * modifier;
            if (a[this.currentSort] > b[this.currentSort]) return 1 * modifier;
            return 0;
        });

        if (this.pageSize === 0) {
            return filtered; // Return all items if pageSize is 0
        }

        const start = (this.currentPage - 1) * this.pageSize;
        const end = start + this.pageSize;
        this.totalItems = filtered.length;
        this.totalSize = filtered.reduce((acc, file) => acc + (file.filesize || 0), 0);
        return filtered.slice(start, end);
    },
    uniqueFolders() {
        const folders = this.files.map(file => file.folder).filter(folder => folder);
        return [...new Set(folders)].sort();
    },
    totalPages: function () {
        if (this.pageSize === 0) return 1;
        return Math.ceil(this.totalItems / this.pageSize);
    },
    pagesToShow() {
        const range = 5;
        let start = Math.max(1, this.currentPage - Math.floor(range / 2));
        let end = Math.min(this.totalPages, start + range - 1);

        if (end - start < range - 1) {
            start = Math.max(1, end - range + 1);
        }

        const pages = [];
        for (let i = start; i <= end; i++) {
            pages.push(i);
        }
        return pages;
    },
    formattedTotalSize() {
        return this.formatFileSize(this.totalSize);
    },
    cardLayout() {
        return this.settings.cardLayout;
    },
    pageSize() {
        return this.settings.pageSize;
    }
};

export const watch = {
    filter: function (newFilter, oldFilter) {
        this.currentPage = 1;
    },
    pageSize: function (newPageSize, oldPageSize) {
        this.currentPage = 1;
    },
    cardLayout(newValue) {
        localStorage.setItem('cardLayout', newValue);
    },
    serverResult: function (newResult) {
        if (newResult) {
            this.showMessage(newResult);
            this.serverResult = null;
        }
    },
    'settings.cardLayout': function(newValue) {
        this.saveSettings();
    },
    'settings.pageSize': function(newValue) {
        this.saveSettings();
    },
};

export const addKeyUpListener = (vueContext) => {
    window.addEventListener('keyup', vueContext.handleKeyup);
}
export const removeKeyUpListener = (vueContext) => {
    window.removeEventListener('keyup', vueContext.handleKeyup);
}