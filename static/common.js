// common.js
export const data = {
    files: [],
    filter: '',
    videoUrl: '',
    loading: false,
    currentSort: 'created',
    currentSortDir: 'desc',
    serverOutput: '',
    serverResult: null,
    currentThumbnail: null,
    currentPage: 1,
    pageSize: 10,
    totalItems: 0,
    totalSize: 0,
    confirmData: {},
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
        this.currentPage = page;
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
    fetchFiles: debounce(function (library=false) {
            console.log('Fetching files');
            const scrollPosition = window.scrollY;
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
                    setTimeout(() => window.scrollTo(0, scrollPosition));
                })
                .catch(error => {
                    console.error('There was an error fetching the files:', error);
                    this.loading = false;
                })
        }, 3000),
    generateThumbnails(library=false) {
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

};

export const computed = {
    filteredFiles: function () {
        let filtered = this.files.filter(file => {
            return file.filename.toLowerCase().includes(this.filter.toLowerCase());
        });


        filtered = filtered.sort((a, b) => {
            let modifier = 1;
            if (this.currentSortDir === 'desc') modifier = -1;
            if (a[this.currentSort] < b[this.currentSort]) return -1 * modifier;
            if (a[this.currentSort] > b[this.currentSort]) return 1 * modifier;
            return 0;
        });

        const start = (this.currentPage - 1) * this.pageSize;
        const end = start + this.pageSize;
        this.totalItems = filtered.length;
        this.totalSize = filtered.reduce((acc, file) => acc + (file.filesize || 0), 0);
        return filtered.slice(start, end);
    },
    totalPages: function () {
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
};

export const watch = {
    filter: function (newFilter, oldFilter) {
        this.currentPage = 1;
    },
    serverResult: function (newResult) {
        if (newResult) {
            this.showMessage(newResult);
            this.serverResult = null;
        }
    },
};