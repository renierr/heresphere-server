import {showToast, handleViewChange, formatDate, playVideo, showConfirmDialog, apiCall, videoUrl} from "helper";
import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
    <h4 class="mt-4">Videos streamed and saved in DB</h4>

    <hs-loading v-if="sharedState.loading"></hs-loading>
    <div v-else>
      <div class="pagination mb-4 d-flex flex-column flex-md-row align-items-center justify-content-between">
        <ul v-if="totalPages > 1" class="pagination mb-0">
          <li class="page-item" :class="{ disabled: currentPage === 1 }">
            <a class="page-link" href="#" @click.prevent="changePage(1)">First</a>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === 1 }">
            <a class="page-link" href="#" @click.prevent="changePage(currentPage - 1)">Previous</a>
          </li>
          <li v-if="pagesToShow[0] > 1" class="page-item disabled d-none d-sm-block">
            <span class="page-link">...</span>
          </li>
          <li v-for="page in pagesToShow" :key="page" class="page-item d-none d-sm-block"
              :class="{ active: currentPage === page }">
            <a class="page-link" href="#" @click.prevent="changePage(page)">{{ page }}</a>
          </li>
          <li v-if="pagesToShow[pagesToShow.length - 1] < totalPages" class="page-item disabled d-none d-sm-block">
            <span class="page-link">...</span>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === totalPages }">
            <a class="page-link" href="#" @click.prevent="changePage(currentPage + 1)">Next</a>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === totalPages }">
            <a class="page-link" href="#" @click.prevent="changePage(totalPages)">Last</a>
          </li>
        </ul>
        <span v-if="totalPages > 1" class="p-2">Page {{ currentPage }}&nbsp;/&nbsp;{{ totalPages }}</span>
        <span class="p-2">Items&nbsp;total {{ totalItems }}</span>
      </div>
      <div class="container mt-4">
            <div class="row row-cols-1 row-cols-sm-2 row-cols-md-3 g-4">
                <div class="col" v-for="online in filteredOnlines" :key="online.url">
                    <div class="card h-100 d-flex flex-column">
                        <img v-if="online.thumbnail" :src="online.thumbnail" class="card-img-top" :alt="online.title" />
                        <div class="card-body flex-grow-1">
                            <h5 class="card-title text-truncate" data-bs-toggle="tooltip" :title="online.title">
                                <a class="video-link text-decoration-none" :href="online.url">
                                    <i class="bi bi-link-45deg"></i>&nbsp;{{ online.title }}
                                </a>
                            </h5>
                            <p class="mb-0">
                                <span v-if="online.resolution" class="text-nowrap me-2"><i class="bi bi-aspect-ratio"></i> {{ online.resolution }}</span>
                            </p>
                            <p v-if="online.date" class="mb-0"><i class="bi bi-calendar"></i> {{ formatDate(online.date) }} (Added)</p>
                            <p v-if="online.download_date" class="mb-0"><i class="bi bi-calendar"></i> {{ formatDate(online.download_date) }} (Downloaded)</p>
                            <p v-if="online.stream_count" class="mb-0"><i class="bi bi-activity"></i> {{ online.stream_count }} (Times Streamed)</p>
                        </div>
                        <div class="card-footer p-2 d-flex flex-wrap gap-2">
                            <button v-if="online.url" class="btn btn-outline-success btn-sm m-1" @click="playOnlineVideo(online)">
                                <i class="bi bi-play-fill"></i> Play
                            </button>
                            <a v-if="online.original_url" class="btn btn-outline-secondary btn-sm m-1" :href="online.original_url" target="_blank"><i class="bi bi-link"></i> Original Link</a>
                            <div class="btn-group" role="group">
                                <button type="button" class="btn btn-outline-secondary btn-sm dropdown-toggle m-1" data-bs-toggle="dropdown" aria-expanded="false">
                                  <i class="bi bi-gear-fill"></i> Actions
                                </button>
                                <ul class="dropdown-menu">
                                  <li><button v-if="online.original_url && !online.download_date" class="dropdown-item" @click="downloadOnlineVideo(online)"><i class="bi bi-download text-secondary"></i> Download</button></li>
                                  <li><button class="dropdown-item" @click="confirmDeleteOnline(online)"><i class="bi bi-trash text-danger"></i> Delete</button></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
`

export const Online = {
    template: template,
    setup() {
        return { sharedState, settings, formatDate, videoUrl };
    },
    data() {
        return {
            onlines: [],
            currentPage: 1,
            pageSize: 9,
        }
    },
    computed: {
        filteredOnlines() {
            const start = (this.currentPage - 1) * this.pageSize;
            const end = start + this.pageSize;
            return this.onlines.slice(start, end);
        },
        totalItems() {
            return this.onlines.length;
        },
        totalPages() {
            if (this.pageSize <= 0) return 1;
            return Math.ceil(this.totalItems / this.pageSize);
        },
        pagesToShow() {
            const totalPages = Math.ceil(this.totalItems / this.pageSize);
            const pages = [];
            const startPage = Math.max(1, this.currentPage - 2);
            const endPage = Math.min(totalPages, this.currentPage + 2);
            for (let i = startPage; i <= endPage; i++) {
                pages.push(i);
            }
            return pages;
        }
    },
    methods: {
        fetchOnlines() {
            sharedState.loading = true;
            fetch('/api/onlines')
                .then(response => response.json())
                .then(data => {
                    this.onlines = data;
                    sharedState.loading = false;
                })
                .catch(error => {
                    showToast('Error fetching onlines');
                    console.error('There was an error fetching the onlines:', error);
                    sharedState.loading = false;
                });
        },
        changePage(page) {
            const totalPages = this.totalPages;
            if (page < 1) {
                this.currentPage = 1;
            } else if (page > totalPages) {
                this.currentPage = totalPages;
            } else {
                this.currentPage = page;
            }
        },
        playOnlineVideo(online) {
            // map the online object to a video player compatible format
            const file = {
                filename: online.url,
                title: online.title || 'Online Video',
            };
            playVideo(file)
        },
        confirmDeleteOnline(online) {
            const confirmData = {
                title: 'Delete Online tracked entry',
                message: `Are you sure you want to delete the tracked online entry from DB?`,
                url: online.original_url,
                file: online.title,
                submit: 'Delete',
                action: this.deleteOnlineEntry,
            }
            showConfirmDialog(confirmData);
        },
        deleteOnlineEntry(confData) {
            if (!confData && !confData.file) {
                showToast('Wrong number of parameters for OnlineEntry');
                return;
            }
            const url = confData.url;
            const utf8Bytes = new TextEncoder().encode(url);
            const encodedUrl = btoa(String.fromCharCode(...utf8Bytes));
            apiCall(`/api/onlines?url=${encodeURIComponent(encodedUrl)}`, { errorMessage: 'Error deleting entry',
                options: { method: 'DELETE'} })
                .then(data => {
                    this.fetchOnlines();
                });
        },
        downloadOnlineVideo(online) {
            if (!online.original_url) {
                showToast('No original URL available for download');
                return;
            }
            handleViewChange('')
            setTimeout(() => {
                videoUrl(online.original_url);
            })
        }
    },
    mounted() {
        this.fetchOnlines();
    }
}
