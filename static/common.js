import {settings, sharedState} from "shared-state";
import {showToast, fetchFiles} from "helper";

let previewVideoWarningAlreadyShown = false;

// TODO remove me
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
    settings: localStoreSettingsLoading(), // TODO remove me
};


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
        this.similarVideos = null;
        this.currentFile = file;
        window.similarityModal.show();
        fetch('/api/similar', {
            method: 'POST',
            body: JSON.stringify({ video_path: file.filename, threshold: this.settings.similarThreshold }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(data => {
                this.similarVideos = data;
            })
            .catch(error => {
                console.error('Error:', error);
                this.serverResult = 'Error calling similars';
                this.similarVideos = [];
            });
    },
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

    showMessage: function (input, options = {}) {
        showToast(input, options);
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
                fetchFiles(true);
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
                fetchFiles(true);
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
                    <option value="~videos~">Move to videos folder</option>
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
              fetchFiles(true);
          })
          .catch(error => {
              console.error('Error moving file:', error);
              this.serverResult = 'Error moving file: ' + error;
          });

    },


};

export const computed = {
    filteredFiles: function () {

        let filtered = sharedState.files.filter(file => {
            const matchesFolder = sharedState.selectedFolder ? file.folder === sharedState.selectedFolder || (file.folder === '' && sharedState.selectedFolder === '~root~') : true;
            const titleCompareValue = (file.title || file.filename.split('/').pop().split('.').slice(0, -1).join('.')).toLowerCase();
            const matchesFilter = sharedState.filter ? titleCompareValue.includes(sharedState.filter.toLowerCase()) : true;
            const matchesResolution = sharedState.selectedResolution ? this.checkResolution(file) : true;
            const matchesDuration = sharedState.selectedDuration ? this.checkDuration(file) : true;
            return matchesFolder && matchesFilter && matchesResolution && matchesDuration;
        });

        const sortCriteria = sharedState.currentSort.split(' ');
        filtered = filtered.sort((a, b) => {
            for (let criterion of sortCriteria) {
                let modifier = 1;
                if (sharedState.currentSortDir === 'desc') modifier = -1;
                if (a[criterion] < b[criterion]) return -1 * modifier;
                if (a[criterion] > b[criterion]) return 1 * modifier;
            }
            return 0;
        });

        sharedState.totalItems = filtered.length;
        sharedState.totalSize = filtered.reduce((acc, file) => acc + (file.filesize || 0), 0);

        if (settings.pageSize === 0) {
            return filtered; // Return all items if pageSize is 0
        }
        const start = (sharedState.currentPage - 1) * settings.pageSize;
        const end = start + settings.pageSize;
        return filtered.slice(start, end);
    },
    cardLayout() {
        return this.settings.cardLayout;
    },
};

export const watch = {
    filter: function (newFilter, oldFilter) {
        sharedState.currentPage = 1;
    },
    pageSize: function (newPageSize, oldPageSize) {
        sharedState.currentPage = 1;
    },
    selectedFolder: function (newFolder, oldFolder) {
        sharedState.currentPage = 1;
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
};

