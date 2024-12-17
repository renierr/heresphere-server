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
    fetchFiles: function (library=false) {
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
            });
    },
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
        return filtered.slice(start, end);
    },
    totalPages: function () {
        return Math.ceil(this.files.length / this.pageSize);
    },
}