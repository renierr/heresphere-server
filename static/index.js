new Vue({
    el: '#app',
    data: {
        files: [],
        filter: '',
        videoUrl: '',
        loading: false,
        currentSort: 'created',
        currentSortDir: 'desc',
        serverOutput: '',
        downloadProgress: {},
        serverResult: null,
        currentThumbnail: null,
        currentPage: 1,
        pageSize: 10,
    },
    methods: {
        redownload: function (url) {
            this.videoUrl = url;
            this.postVideoUrl();
        },
        fetchFiles: function () {
            this.loading = true;
            fetch('/api/list')
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
                });
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
        formatDate(epochSeconds) {
            if (epochSeconds < 1) {
                return '';
            }
            const date = new Date(epochSeconds * 1000);
            const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' };
            return date.toLocaleDateString(undefined, options);
        },
        copyToClipboard: function (event, text) {
            event.preventDefault();
            navigator.clipboard.writeText(text).then(() => {
                alert('Link copied to clipboard');
            }).catch(err => {
                console.error('Failed to copy: ', err);
            });
        },
        cleanup() { // Add this method
            fetch('/cleanup')
                .then(response => response.json())
                .then(data => {
                    this.serverResult = JSON.stringify(data);
                    this.fetchFiles();
                })
                .catch(error => {
                    console.error('Error:', error);
                    this.serverResult = 'Error occurred during cleanup';
                });
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
                    this.serverResult = data.success ? 'Thumbnails generated successfully' : 'Failed to generate thumbnails';
                })
                .catch(error => {
                    console.error('Error generating thumbnails:', error);
                    this.serverResult = 'Error generating thumbnails';
                });
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
                    this.serverResult = data.success ? 'Thumbnail generated successfully' : 'Failed to generate thumbnail';
                })
                .catch(error => {
                    console.error('Error generating thumbnail:', error);
                    this.serverResult = 'Error generating thumbnails';
                });

        },
        openThumbnail(thumbnail) {
            this.currentThumbnail = thumbnail;
            const modal = new bootstrap.Modal(document.getElementById('thumbnailModal'));
            modal.show();
        },
        changePage(page) {
            this.currentPage = page;
        },
    },
    computed: {
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
            return filtered.slice(start, end);
        },
        getProgressForId: function () {
            return function (id) {
                return this.downloadProgress[id] || 0;
            };
        },
        totalPages: function () {
            return Math.ceil(this.files.length / this.pageSize);
        },
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
    }
});
