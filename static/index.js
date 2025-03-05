import {
    data,
    methods,
    computed,
    watch,
    addSwipeNavigationForPagingListener, addKeyNavigationForPagingListener, removeKeyNavigationForPagingListener
} from './common.js';

import { createApp } from './js/vue.esm-browser.js';
import { eventBus } from './js/event-bus.js';

const app = createApp({
    data() {
        return {
            ...data,
            downloadProgress: {},
            removeSseListener: null,
        }
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
                                window.videoModal.hide();
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
                            window.videoModal.show();
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
        settings: {
            handler() {
                console.log('Settings changed');
                this.saveSettings()
            },
            deep: true,
        }
    },
    beforeUnmount() {
        removeKeyNavigationForPagingListener(this);
        if (this.removeSseListener) {
            this.removeSseListener();
        }
        eventBus.events = {};
    },
    mounted() {
        window.vueInstance = this;    // store vue instance in DOM
        addKeyNavigationForPagingListener(this);
        addSwipeNavigationForPagingListener(this);
        this.fetchFiles();
        this.removeSseListener = eventBus.on('sse-message', (data) => {
            let progressExp = data.match(/(\d+.\d+)% complete/);
            let progressId = data.match(/Downloading...\[(\d+)]/);
            if (progressId) {
                this.downloadProgress = this.downloadProgress || {};
                this.downloadProgress[progressId[1]] = progressExp ? parseFloat(progressExp[1]) : 0;
            }

            if (data.includes('Download failed')) {
                let progressId = data.match(/Download failed \[(\d+)]/);
                if (progressId) {
                    this.downloadProgress[progressId[1]] = 0;
                }
            }

            if (data.includes('Download finished') ||
              data.includes('Generate thumbnails finished') ||
              data.includes(' 0.0% complete')) {
                this.fetchFiles();
            }
        });
    },
});

app.config.errorHandler = function (err, instance, info) {
    // Log the error details to the console
    console.error(`Error: ${err.toString()}\nInfo: ${info}`);

    // Display a user-friendly message in Bootstrap toast
    const toastElement = document.getElementById('serverResultToast');
    const toastTitle = document.getElementById('serverResultTitle');
    const toastMessage = document.getElementById('serverResultMessage');

    toastTitle.textContent = 'An error occurred';
    toastMessage.textContent = err.toString();

    const toast = new bootstrap.Toast(toastElement, { autohide: false });
    toast.show();
};

app.config.globalProperties.$saveSettings = function () {
    this.saveSettings();
}

import { ServerInfo } from './js/components/server-info.js';
app.component('server-info', ServerInfo);
app.mount('#app');

