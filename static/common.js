let previewVideoWarningAlreadyShown = false;

function localStoreSettingsLoading() {
    const defaults = { cardLayout: true, pageSize: 12,
        filterAccordionOpen: true, infoAccordionOpen: true, lastMoveSubfolder: '', showVideoPreview: true, similarThreshold: 50 };
    let storedSetting = JSON.parse(localStorage.getItem('settings')) || {};
    storedSetting = {...defaults, ...storedSetting};
    return storedSetting;
}

// common.js
export const data = {
    files: [],
    filter: '',
    videoUrl: '',
    selectedFolder: '',
    selectedResolution: '',
    selectedDuration: 0,
    loading: false,
    currentSort: 'created',
    currentSortDir: 'desc',
    serverOutput: '',
    serverResult: null,
    currentFile: null,
    similarVideos: null,
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
    showSimilar(file) {
        fetch('/api/similar', {
            method: 'POST',
            body: JSON.stringify({ video_path: file.filename, threshold: this.settings.similarThreshold }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(data => {
                this.currentFile = file;
                this.similarVideos = data;
                window.similarityModal.show();
            })
            .catch(error => {
                console.error('Error:', error);
                this.serverResult = 'Error calling similars';
            });
    },
    fetchFiles: debounce(function (restoreScrollPosition=false) {
            console.log('Fetching files');
            // if we are in library url path we should use library api
            const library = window.location.pathname.includes('/library');
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
                    this.files = data.map(file => ({
                        ...file,
                        showPreview: false,
                    }));
                    this.loading = false;
                    if (restoreScrollPosition) {
                        console.log('Restoring scroll position', scrollPosition);
                        setTimeout(() => window.scrollTo(0, scrollPosition));
                    }
                })
                .catch(error => {
                    console.error('There was an error fetching the files:', error);
                    this.loading = false;
                })
        }, 3000),
    startPreview(file, evt) {
        evt.target.play()
            .then(() => file.showPreview = true)
            .catch(error => {
            if (error.name === 'NotAllowedError' && !previewVideoWarningAlreadyShown) {
                this.showMessage('Please interact with the document (e.g., click or press a key) before video preview playing is allowed.');
                previewVideoWarningAlreadyShown = true;
            }
        });
    },
    stopPreview(file, evt) {
        evt.target.currentTime = 0;
        evt.target.pause();
        file.showPreview = false;
    },
    generateThumbnails() {
        fetch('/api/generate_thumbnails', {
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
    confirmUpdate() {
        this.confirmData = {
            title: 'Server Update',
            message: `This will call a Server Update. The process might be killed and connection can get lost, Are you sure you want to proceed?`,
            submit: 'Update',
            action: this.updateServer,
        }
        window.confirmModal.show();

    },
    updateServer() { // Add this method
        fetch('/update')
            .then(response => response.json())
            .then(data => {
                this.serverResult = data;
            })
            .catch(error => {
                console.error('Error:', error);
                this.serverResult = 'Server may lost connection after update see Info box or reload page';
            });
    },
    confirmCleanup() {
        this.confirmData = {
            title: 'Cleanup files',
            message: `This will clean the download tracked files and find orphan thumbnails and delete them, Are you sure you want to proceed?`,
            submit: 'Cleanup',
            action: this.cleanup,
        }
        window.confirmModal.show();
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
    scanFiles: function () {
        fetch('/scan')
          .then(response => response.json())
          .then(data => {
              this.serverResult = data;
          })
          .catch(error => {
              console.error('Error:', error);
              this.serverResult = 'Error clearing cache';
          });
    },
    showMessage: function (input, options = {}) {
        const { title = 'Message', stayOpen = false, asHtml = false } = options;
        const toastElement = document.getElementById('serverResultToast');
        const toastTitle = document.getElementById('serverResultTitle');
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
        if (asHtml) {
            toastTitle.innerHTML = title;
            toastMessage.innerHTML = message;
        } else {
            toastTitle.textContent = title;
            toastMessage.textContent = message;
        }

        const toast = new bootstrap.Toast(toastElement, { autohide: !options.stayOpen });
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
        window.confirmModal.show();
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
                this.fetchFiles(true);
            })
            .catch(error => {
                console.error('Error deleting bookmark:', error);
            });
    },
    playVideo(file) {
        const videoModalBody = document.getElementById('videoModalBody');
        const videoModalTitle = document.getElementById('videoModalLabel');
        const videoModalFooter = document.getElementById('videoModalFooter');

        videoModalFooter.innerHTML = '';
        videoModalTitle.textContent = file.title || 'Video Player';
        videoModalBody.innerHTML = `
            <video-js id="videoPlayer" class="vjs-default-skin w-100" controls autoplay>
                <source src="${file.filename}" type="video/mp4">
            </video-js>
        `;
        videojs('videoPlayer');
        window.videoModal.show();
    },
    saveSettings() {
        localStorage.setItem('settings', JSON.stringify(this.settings));
    },
    toggleFilterAccordion() {
        this.settings.filterAccordionOpen = !this.settings.filterAccordionOpen;
        this.saveSettings();
    },
    toggleInfoAccordion() {
        this.settings.infoAccordionOpen = !this.settings.infoAccordionOpen;
        this.saveSettings();
    },
    checkResolution(file) {
        if (this.selectedResolution === 'HD') {
            return file.width > 1900 || file.height > 1900;
        } else if (this.selectedResolution === '4K') {
            return file.width >= 3800 || file.height >= 3800;
        } else if (this.selectedResolution === '8K') {
            return file.width >= 8000 || file.height >= 8000;
        }
        return true;
    },
    checkDuration(file) {
        const durationInMinutes = file.duration / 60;
        return durationInMinutes >= this.selectedDuration;
    },
    showDuplicateInfo(file) {
        if (file.may_exist) {
            let message = file.may_exist.split('\n');
            message = message.map((line) => {
                if (line.includes('id[')) {
                    return `<h5>${line}</h5>`
                } else {
                    return `<p>${line}</p>`;
                }
            }).join('<br>');
            this.showMessage(message, {title: "Duplicates", stayOpen: true, asHtml: true});
        }
    },
    openAndHandleSSEConnection(call_func) {
        const eventSource = new EventSource('/sse');
        window.addEventListener('beforeunload', () => {
            eventSource.close();
            console.log('EventSource connection closed');
        });

        const serverOutput = [];
        eventSource.onmessage = event => {
            // ignore Heartbeat message
            if (event.data.includes('Heartbeat '))  return;

            serverOutput.push(new Date().toLocaleTimeString() + ': ' + event.data);
            if (serverOutput.length > 100) {
                serverOutput.shift();
            }
            this.serverOutput = serverOutput.slice().reverse().join('\n');
            if (call_func)  {
                call_func(event);
            }
        };
        return eventSource;
    },
    confirmRenameFile(file) {
        const modalConfirmExtras = document.getElementById('confirmModalExtras');
        const currentName = file.title || file.filename.split('/').pop().split('.').slice(0, -1).join('.');;
        modalConfirmExtras.innerHTML = `
            <div class="d-flex align-items-center flex-column flex-md-row">
                <input id="confModal_fileName" class="form-control" type="text" />
            </div>
            `;
        const nameInput = document.getElementById('confModal_fileName');
        nameInput.value = currentName;
        this.confirmData = {
            title: 'Rename file',
            message: `Rename the title for the following file:`,
            file: file.filename,
            submit: 'Rename',
            action: (confData) => {
                let newName = nameInput.value;
                if (newName === currentName) {
                    this.showMessage('New name is the same as the current name');
                    return;
                }
                this.renameFile(confData, newName);
            },
        }
        window.confirmModal.show();
        nameInput.addEventListener('keydown', (evt) => {
            if (evt.key === 'Enter') {
                evt.preventDefault();
                window.confirmModal.hide();
                this.confirmData.action(this.confirmData)
            }
        });

    },
    renameFile(confData, newName) {
        if (!confData && !confData.file) {
            this.showMessage('Wrong number of parameters for move to library');
            return;
        }
        const file = confData.file;
        this.confirmData = {};
        fetch('/api/rename', {
            method: 'POST',
            body: JSON.stringify({ video_path: file, newName: newName }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(data => {
                this.serverResult = data;
                this.fetchFiles(true);
            })
            .catch(error => {
                console.error('Error renaming file:', error);
                this.serverResult = 'Error renaming file: ' + error;
            });
    },
    toggleFavorite(file) {
        fetch('/api/toggle_favorite', {
            method: 'POST',
            body: JSON.stringify({ video_path: file.filename }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
          .then(response => response.json())
          .then(data => {
              this.serverResult = data;
              file.favorite = !file.favorite;
          })
          .catch(error => {
              console.error('Error favorite toggle for file:', error);
              this.serverResult = 'Error favorite toggle for file: ' + error;
          });
    },
    confirmMoveFile(file) {
        const lastFolder = this.settings.lastMoveSubfolder || '';
        const modalConfirmExtras = document.getElementById('confirmModalExtras');
        const options = library_subfolders.map(subfolder => {
            const selected = subfolder === lastFolder ? 'selected' : '';
            return `<option value="${subfolder}" ${selected}>${subfolder}</option>`;
        }).join('');
        modalConfirmExtras.innerHTML = `
            <div class="d-flex align-items-center flex-column flex-md-row">
                <label for="subfolderSelect" class="form-label me-2 text-nowrap">Target Subfolder</label>
                <select id="subfolderSelect" class="form-select">
                    <option value="">Move to library root folder</option>
                    <option value="~videos~">Move to videos root folder</option>
                    ${options}
                </select>
            </div>
            `;
        this.confirmData = {
            title: 'Move file',
            message: `Are you sure you want to move the following file inside library?`,
            file: file.filename,
            submit: 'Move',
            action: (confData) => {
                let subfolderSelection = document.getElementById('subfolderSelect').value;
                if (file.folder === subfolderSelection) {
                    this.showMessage('Cannot move file inside its own folder');
                    return;
                }
                this.moveFile(confData, subfolderSelection);
            },
        }
        window.confirmModal.show();
    },
    moveFile(confData, subfolder) {
        if (!confData && !confData.file) {
            this.showMessage('Wrong number of parameters for move to library');
            return;
        }
        const file = confData.file;
        this.settings.lastMoveSubfolder = subfolder;
        this.saveSettings();
        this.confirmData = {};
        fetch('/api/move_file', {
            method: 'POST',
            body: JSON.stringify({ video_path: file, subfolder: subfolder }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
          .then(response => response.json())
          .then(data => {
              this.serverResult = data;
              this.fetchFiles(true);
          })
          .catch(error => {
              console.error('Error moving file:', error);
              this.serverResult = 'Error moving file: ' + error;
          });

    },


};

export const computed = {
    filteredFiles: function () {

        let filtered = this.files.filter(file => {
            const matchesFolder = this.selectedFolder ? file.folder === this.selectedFolder || (file.folder === '' && this.selectedFolder === '~root~') : true;
            const titleCompareValue = (file.title || file.filename.split('/').pop().split('.').slice(0, -1).join('.')).toLowerCase();
            const matchesFilter = this.filter ? titleCompareValue.includes(this.filter.toLowerCase()) : true;
            const matchesResolution = this.selectedResolution ? this.checkResolution(file) : true;
            const matchesDuration = this.selectedDuration ? this.checkDuration(file) : true;
            return matchesFolder && matchesFilter && matchesResolution && matchesDuration;
        });

        const sortCriteria = this.currentSort.split(' ');
        filtered = filtered.sort((a, b) => {
            for (let criterion of sortCriteria) {
                let modifier = 1;
                if (this.currentSortDir === 'desc') modifier = -1;
                if (a[criterion] < b[criterion]) return -1 * modifier;
                if (a[criterion] > b[criterion]) return 1 * modifier;
            }
            return 0;
        });

        this.totalItems = filtered.length;
        this.totalSize = filtered.reduce((acc, file) => acc + (file.filesize || 0), 0);

        if (this.pageSize === 0) {
            return filtered; // Return all items if pageSize is 0
        }
        const start = (this.currentPage - 1) * this.pageSize;
        const end = start + this.pageSize;
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
    selectedFolder: function (newFolder, oldFolder) {
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
    'settings.showVideoPreview': function(newValue) {
        this.saveSettings();
    },
    'settings.similarThreshold': function(newValue) {
        this.saveSettings();
    },
};

function keyNavigationForPaging(event, vueContext) {
    // only if paging present
    if (vueContext.totalPages === 1) return;

    // check if currently an input is focused
    if (document.activeElement.tagName === 'INPUT' || document.querySelector('.modal.show')) return;

    if (event.key === 'ArrowLeft') {
        vueContext.changePage(vueContext.currentPage - 1);
    } else if (event.key === 'ArrowRight') {
        vueContext.changePage(vueContext.currentPage + 1);
    }
}

let keyNavigationForPagingHandler;
export const addKeyNavigationForPagingListener = (vueContext) => {
    keyNavigationForPagingHandler = (event) => keyNavigationForPaging(event, vueContext);
    window.addEventListener('keyup', keyNavigationForPagingHandler);
}
export const removeKeyNavigationForPagingListener = () => {
    if (keyNavigationForPagingHandler) {
        window.removeEventListener('keyup', keyNavigationForPagingHandler);
        keyNavigationForPagingHandler = null;
    }
}

let swipeNavigationForPagingHandler;
export const addSwipeNavigationForPagingListener = (vueContext) => {
    const hammer = new Hammer(document.body);
    hammer.get('swipe').set({ threshold: 50 });
    hammer.on('swipe', (event) => {
        if (document.activeElement.tagName === 'INPUT' || document.querySelector('.modal.show')) return;
        if (event.direction === Hammer.DIRECTION_LEFT) {
            vueContext.changePage(vueContext.currentPage + 1);
        } else if (event.direction === Hammer.DIRECTION_RIGHT) {
            vueContext.changePage(vueContext.currentPage - 1);
        }
    });
}
