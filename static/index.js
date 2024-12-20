import { data, methods, computed, watch } from './common.js';

new Vue({
    el: '#app',
    data: {
        ...data,
        downloadProgress: {},
    },
    methods: {
        ...methods,
        redownload(url) {
            this.videoUrl = url;
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
                    this.serverResult = data;
                    if (stream) {
                        const url_to_play = data.videoUrl.replace(/\/$/, '');
                        this.serverResult = 'Stream file at: ' + url_to_play;
                        window.open('', '_blank').document.write(`
                            <html>
                                <head>
                                    <title>Video Player</title>
                                </head>
                                <body>
                                    <p>If the video does not start, <a href="${url_to_play}">click here</a>.</p>
                                    <video controls autoplay style="width: 100%; height: 100%;">
                                        <source src="${url_to_play}" type="video/mp4">
                                        Your browser does not support the video tag.
                                    </video>
                                </body>
                            </html>
                        `);
                    } else {
                        this.serverResult = data;
                    }
                    this.videoUrl = '';
                })
                .catch(error => {
                    this.serverResult = 'Error download/stream file: ' + error;
                    console.error('Error:', error);
                });
        },
        copyToClipboard: function (event, text) {
            event.preventDefault();
            navigator.clipboard.writeText(text).then(() => {
                this.showMessage('Copied to clipboard');
            }).catch(err => {
                console.error('Failed to copy: ', err);
            });
        },
        confirmMoveToLibrary(filename) {
            if (confirm("Are you sure you want to move this file to the library?")) {
                this.moveToLibrary(filename);
            }
        },
        moveToLibrary(file) {
            fetch('/api/move_to_library', {
                method: 'POST',
                body: JSON.stringify({ video_path: file }),
                headers: {
                    'Content-Type': 'application/json'
                }
            })
                .then(response => response.json())
                .then(data => {
                    this.serverResult = data;
                    this.fetchFiles();
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
    mounted: function () {
        this.fetchFiles();
        const eventSource = new EventSource('/sse');
        const serverOutput = [];
        eventSource.onmessage = event => {
            let progressExp = event.data.match(/(\d+.\d+)% complete/);
            let progressId = event.data.match(/Downloading...\[(\d+)]/);
            if (progressId) {
                this.downloadProgress = this.downloadProgress || {};
                this.downloadProgress[progressId[1]] = progressExp ? parseFloat(progressExp[1]) : 0;
            }
            serverOutput.push(new Date().toLocaleTimeString() + ': ' + event.data);
            if (serverOutput.length > 100) {
                serverOutput.shift();
            }
            this.serverOutput = serverOutput.slice().reverse().join('\n');
            if (event.data.includes('Download finished') ||
                event.data.includes('Generate thumbnails finished') ||
                event.data.includes(' 0.0% complete')) {
                this.fetchFiles();
            }
        };
    },
});
