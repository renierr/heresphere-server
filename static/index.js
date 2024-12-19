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
        postVideoUrl() {
            if (this.videoUrl.trim() === '') {
                alert('Please enter a video URL');
                return;
            }
            fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ sourceUrl: this.videoUrl })
            })
                .then(response => response.json())
                .then(data => {
                    this.serverOutput += new Date().toLocaleTimeString() + ': Starting download of ' + this.videoUrl + '\n';
                    this.videoUrl = '';
                })
                .catch(error => {
                    this.serverOutput += new Date().toLocaleTimeString() + ': Error for download of ' + this.videoUrl + ' - ' + error + '\n';
                    console.error('Error:', error);
                });
        },
        copyToClipboard: function (event, text) {
            event.preventDefault();
            navigator.clipboard.writeText(text).then(() => {
                alert('Link copied to clipboard');
            }).catch(err => {
                console.error('Failed to copy: ', err);
            });
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
                event.data.includes('Generated thumbnails finished') ||
                event.data.includes(' 0.0% complete')) {
                this.fetchFiles();
            }
        };
    },
});
