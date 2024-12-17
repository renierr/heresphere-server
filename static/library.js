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
            fetch('/api/library/list')
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
        formatDate(epochSeconds) {
            if (epochSeconds < 1) {
                return '';
            }
            const date = new Date(epochSeconds * 1000);
            const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' };
            return date.toLocaleDateString(undefined, options);
        },
        generateThumbnails() {
            fetch('/api/library/generate_thumbnails', {
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
        totalPages: function () {
            return Math.ceil(this.files.length / this.pageSize);
        },
    },
    mounted: function () {
        this.fetchFiles();
        const eventSource = new EventSource('/sse');
        const serverOutput = [];
        eventSource.onmessage = event => {
            serverOutput.push(new Date().toLocaleTimeString() + ': ' + event.data);
            if (serverOutput.length > 100) {
                serverOutput.shift();
            }
            this.serverOutput = serverOutput.slice().reverse().join('\n');
            if (event.data.includes('Generated thumbnails finished')) {
                this.fetchFiles();
            }
        };
    }
});
