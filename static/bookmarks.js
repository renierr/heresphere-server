import { data, methods, computed, watch } from './common.js';

new Vue({
    el: '#app',
    data: {
        settings: data.settings,
        bookmarks: [],
        newBookmarkTitle: '',
        newBookmarkUrl: '',
        serverOutput: '',
        loading: false,
        confirmData: {},
    },
    methods: {
        toggleInfoAccordion: methods.toggleInfoAccordion,
        showMessage: methods.showMessage,
        openAndHandleSSEConnection: methods.openAndHandleSSEConnection,
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
            if (!this.newBookmarkUrl) {
                this.showMessage('Bookmark URL is required.');
                return;
            }

            // add http:// if not present in url
            if (!this.newBookmarkUrl.startsWith('http')) {
                this.newBookmarkUrl = 'http://' + this.newBookmarkUrl;
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
            const utf8Bytes = new TextEncoder().encode(url);
            const encodedUrl = btoa(String.fromCharCode(...utf8Bytes));
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
        window.vueInstance = this;    // store vue instance in DOM
        this.fetchBookmarks();
        this.openAndHandleSSEConnection();
    }
});
