import { data, methods, computed, watch } from './common.js';

new Vue({
    el: '#app',
    data: {
        bookmarks: [],
        newBookmarkTitle: '',
        newBookmarkUrl: '',
        serverOutput: '',
        loading: false,
        confirmData: {},
    },
    methods: {
        showMessage: methods.showMessage,
        fetchBookmarks() {
            this.loading = true;
            fetch('/api/bookmarks')
                .then(response => response.json())
                .then(data => {
                    this.bookmarks = data;
                    this.loading = false;
                })
                .catch(error => {
                    this.showMessage('Error fetching bookmarks');
                    console.error('There was an error fetching the bookmarks:', error);
                    this.loading = false;
                });
        },
        editBookmark(bookmark) {
            this.newBookmarkTitle = bookmark.title;
            this.newBookmarkUrl = bookmark.url;
        },
        saveBookmark() {
            if (!this.newBookmarkTitle || !this.newBookmarkUrl) {
                this.showMessage('Both title and URL are required.');
                return;
            }

            const newBookmark = {
                title: this.newBookmarkTitle,
                url: this.newBookmarkUrl,
            };
            fetch('/api/bookmarks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newBookmark),
            })
                .then(response => response.json())
                .then(data => {
                    this.newBookmarkTitle = '';
                    this.newBookmarkUrl = '';
                    this.fetchBookmarks();
                })
                .catch(error => {
                    this.showMessage('Error adding bookmark');
                    console.error('Error adding bookmark:', error);
                });
        },
        deleteBookmark(url) {
            if (!url) {
                this.showMessage('URL is required.');
                return;
            }
            const encodedUrl = btoa(url);
            fetch(`/api/bookmarks?url=${encodeURIComponent(encodedUrl)}`, {
                method: 'DELETE',
            })
                .then(response => response.json())
                .then(() => {
                    this.bookmarks = this.bookmarks.filter(bookmark => bookmark.url !== url);
                })
                .catch(error => {
                    console.error('Error deleting bookmark:', error);
                });
        },
    },
    computed: {
    },
    watch: {
    },
    mounted: function () {
        // fetch bookmarks
        this.fetchBookmarks();

        const eventSource = new EventSource('/sse');
        const serverOutput = [];
        eventSource.onmessage = event => {
            serverOutput.push(new Date().toLocaleTimeString() + ': ' + event.data);
            if (serverOutput.length > 100) {
                serverOutput.shift();
            }
            this.serverOutput = serverOutput.slice().reverse().join('\n');
        };
    }
});
