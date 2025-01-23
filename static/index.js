import {
    data,
    methods,
    computed,
    watch,
    addSwipeNavigationForPagingListener, addKeyNavigationForPagingListener, removeKeyNavigationForPagingListener
} from './common.js';

new Vue({
    el: '#app',
    data: {
        ...data,
        downloadProgress: {},
    },
    methods: {
        ...methods,
        redownload(file) {
            this.videoUrl = file.url;
            this.postVideoUrl();
        },
        postVideoUrl(stream=false) {
            if (this.videoUrl.trim() === '') {
                this.serverResult = 'Please enter a URL';
                return;
            }
            fetch(stream ? '/stream' : '/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ sourceUrl: this.videoUrl, url: this.videoUrl })
            })
                .then(response => response.json())
                .then(data => {
                    if (stream) {
                        const video_url = data.videoUrl;
                        const audio_url = data.audioUrl;
                        const videoModal = new bootstrap.Modal(document.getElementById('videoModal'));
                        const videoModalTitle = document.getElementById('videoModalLabel');
                        const modalBody = document.getElementById('videoModalBody');
                        const modalFooter = document.getElementById('videoModalFooter');
                        if (modalBody && modalFooter && video_url) {
                            // strip trailing / from video url
                            const video_source = video_url.replace(/\/+$/, '');
                            const title = data.title || 'Video Streaming...';
                            videoModalTitle.textContent = title;
                            modalBody.innerHTML = `
                                <video-js id="videoPlayer" class="vjs-default-skin w-100 h-100" controls autoplay>
                                    <source src="${video_source}" type="video/webm">
                                </video-js>
                            `;
                            videojs('videoPlayer');
                            modalFooter.innerHTML = `
                                <a href="${this.videoUrl}" target="_blank">Video URL provided</a>
                                <a href="${video_source}" target="_blank">Extracted Video link</a>
                            `;

                            const tempVideoUrl = this.videoUrl;
                            const downloadButton = document.createElement('button');
                            downloadButton.textContent = 'Trigger Download';
                            downloadButton.classList.add('btn', 'btn-primary', 'btn-sm');
                            downloadButton.addEventListener('click', () => {
                                videoModal.hide();
                                this.redownload({ url: tempVideoUrl });
                            });
                            modalFooter.appendChild(downloadButton);

                            if (navigator.share) {
                                const shareButton = document.createElement('button');
                                shareButton.textContent = 'Share Video';
                                shareButton.classList.add('btn', 'btn-secondary', 'btn-sm');
                                shareButton.addEventListener('click', () => {
                                    navigator.share({
                                        title: title,
                                        url: tempVideoUrl,
                                    })
                                        .then(() => console.log(`Successful shared ${tempVideoUrl}`))
                                        .catch((error) => console.log('Error sharing', error));
                                });
                                modalFooter.appendChild(shareButton);
                                const shareExtractedButton = document.createElement('button');
                                shareExtractedButton.textContent = 'Share Extracted Video';
                                shareExtractedButton.classList.add('btn', 'btn-secondary', 'btn-sm');
                                shareExtractedButton.addEventListener('click', () => {
                                    navigator.share({
                                        title: title,
                                        url: video_source,
                                    })
                                      .then(() => console.log(`Successful shared ${tempVideoUrl}`))
                                      .catch((error) => console.log('Error sharing', error));
                                });
                                modalFooter.appendChild(shareExtractedButton);
                            }
                            videoModal.show();
                            this.videoUrl = '';
                        } else {
                            this.serverResult = 'Error: No video URL found to be played';
                        }
                    } else {
                        this.serverResult = data;
                    }
                })
                .catch(error => {
                    this.serverResult = 'Error download/stream file: ' + error;
                    console.error('Error:', error);
                });
        },
        confirmMoveToLibrary(filename) {
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
                    <option value="">Select a subfolder or leave for root folder</option>
                    ${options}
                </select>
            </div>
            `;
            this.confirmData = {
                title: 'Move file',
                message: `Are you sure you want to move the following file to the library?`,
                file: filename,
                submit: 'Move',
                action: (confData) => {
                    let subfolderSelection = document.getElementById('subfolderSelect').value;
                    this.moveToLibrary(confData, subfolderSelection);
                },
            }
            const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
            modal.show();
            // clear extras on modal close
            modal._element.addEventListener('hidden.bs.modal', () => {
                modalConfirmExtras.innerHTML = '';
            });
        },
        moveToLibrary(confData, subfolder) {
            if (!confData && !confData.file) {
                this.showMessage('Wrong number of parameters for move to library');
                return;
            }
            const file = confData.file;
            this.settings.lastMoveSubfolder = subfolder;
            this.saveSettings();
            this.confirmData = {};
            fetch('/api/move_to_library', {
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

    },
    computed: {
        ...computed,
        getProgressForId: function () {
            return function (id) {
                return this.downloadProgress[id] || 0;
            };
        },
    },
    watch: {
        ...watch,
    },
    beforeDestroy() {
        removeKeyNavigationForPagingListener(this);
    },
    mounted: function () {
        window.vueInstance = this;    // store vue instance in DOM
        addKeyNavigationForPagingListener(this);
        addSwipeNavigationForPagingListener(this);
        this.fetchFiles();
        this.openAndHandleSSEConnection((evt) => {
            let progressExp = evt.data.match(/(\d+.\d+)% complete/);
            let progressId = evt.data.match(/Downloading...\[(\d+)]/);
            if (progressId) {
                this.downloadProgress = this.downloadProgress || {};
                this.downloadProgress[progressId[1]] = progressExp ? parseFloat(progressExp[1]) : 0;
            }

            if (evt.data.includes('Download failed')) {
                let progressId = evt.data.match(/Download failed \[(\d+)]/);
                if (progressId) {
                    this.downloadProgress[progressId[1]] = 0;
                }
            }

            if (evt.data.includes('Download finished') ||
              evt.data.includes('Generate thumbnails finished') ||
              evt.data.includes(' 0.0% complete')) {
                this.fetchFiles();
            }
        });
    },
});
