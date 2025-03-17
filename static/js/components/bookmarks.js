import {showToast} from "helper";
import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
    <h3 class="mt-4">A List of Bookmarks</h3>
    <div class="row mt-2 mb-3">
        <div class="col-md-5">
            <div class="form-floating">
                <input type="text" v-model="newBookmarkUrl" class="form-control" id="floatingUrl" placeholder=" ">
                <label for="floatingUrl" class="text-muted">Enter bookmark URL...</label>
            </div>
        </div>
        <div class="col-md-5">
            <div class="form-floating">
                <input type="text" v-model="newBookmarkTitle" class="form-control" id="floatingTitle" placeholder=" ">
                <label for="floatingTitle" class="text-muted">Enter bookmark title...</label>
            </div>
        </div>
        <div class="col-md-2 d-flex align-items-center">
            <button @click="saveBookmark" class="btn btn-primary w-100">Save Bookmark</button>
        </div>
    </div>

    <hs-loading v-if="sharedState.loading"></hs-loading>
    <div v-else>
        <div v-if="bookmarks.length === 0" class="card-body text-center">No Bookmarks present</div>
        <ul class="list-group list-group-flush">
            <li v-for="bookmark in bookmarks" :key="bookmark.url" class="list-group-item mb-2 rounded border-1 p-1">
                <div class="w-100 d-flex flex-column flex-sm-row justify-content-between align-items-start gap-1">
                    <div class="text-break flex-grow-1">
                        <a :href="bookmark.url" target="_blank" rel="noopener noreferrer external" @click.prevent="openInNativeBrowser(bookmark.url)"> <i class="bi bi-link-45deg"></i>&nbsp;{{ bookmark.title || bookmark.url }}</a>
                        <p class="mb-0 text-muted small">{{ bookmark.url }}</p>
                    </div>
                    <div class="bookmark-function text-end">
                        <button @click="editBookmark(bookmark)" class="btn btn-sm btn-outline-primary btn-sm m-1">Edit</button>
                        <button @click="deleteBookmark(bookmark.url)" class="btn btn-sm btn-outline-danger btn-sm m-1">Delete</button>
                    </div>
                </div>
            </li>
        </ul>
    </div>

    <footer class="footer py-3">
        <div class="text-center mt-4">
            <div class="d-grid gap-2 d-sm-flex justify-content-sm-center">
                <a href="/static/bookmarks.json" download="bookmarks.json" class="btn btn-secondary">Download All Bookmarks</a>
            </div>
        </div>
    </footer>

`

export const Bookmarks = {
    template: template,
    setup() {
        return { sharedState, settings };
    },
    data() {
        return {
            bookmarks: [],
            newBookmarkTitle: '',
            newBookmarkUrl: '',
        }
    },
    methods: {
        fetchBookmarks() {
            sharedState.loading = true;
            fetch('/api/bookmarks')
                .then(response => response.json())
                .then(data => {
                    this.bookmarks = data;
                    sharedState.loading = false;
                })
                .catch(error => {
                    showToast('Error fetching bookmarks');
                    console.error('There was an error fetching the bookmarks:', error);
                    sharedState.loading = false;
                });
        },
        openInNativeBrowser(url) {
            window.open(url, '_blank', 'noopener,noreferrer');
        },
        editBookmark(bookmark) {
            this.newBookmarkTitle = bookmark.title;
            this.newBookmarkUrl = bookmark.url;
        },
        saveBookmark() {
            if (!this.newBookmarkUrl) {
                showToast('Bookmark URL is required.');
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
                    showToast('Error adding bookmark');
                    console.error('Error adding bookmark:', error);
                });
        },
        deleteBookmark(url) {
            if (!url) {
                showToast('URL is required.');
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
    mounted() {
        this.fetchBookmarks()
    }
}