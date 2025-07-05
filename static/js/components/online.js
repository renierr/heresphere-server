import {showToast, handleViewChange, formatDate, playVideo, showConfirmDialog, apiCall, fetchFiles} from "helper";
import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
    <h3 class="mt-4">all videos streamed before and saved in DB</h3>

    <hs-loading v-if="sharedState.loading"></hs-loading>
    <div v-else>
        <div class="container mt-4">
            <div class="row row-cols-1 row-cols-sm-2 row-cols-md-3 g-4">
                <div class="col" v-for="online in onlines" :key="online.url">
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
                            <p v-if="online.date" class="mb-0"><i class="bi bi-calendar"></i> {{ formatDate(online.date) }} (Last Streamed)</p>
                            <p v-if="online.stream_count" class="mb-0"><i class="bi bi-activity"></i> {{ online.stream_count }} (Times Streamed)</p>
                        </div>
                        <div class="card-footer p-2 d-flex flex-wrap gap-2">
                            <button v-if="online.url" class="btn btn-outline-success btn-sm m-1" @click="playOnlineVideo(online)">
                                <i class="bi bi-play-fill"></i> Play
                            </button>
                            <a v-if="online.original_url" class="btn btn-outline-secondary btn-sm m-1" :href="online.original_url" target="_blank"><i class="bi bi-link"></i> Original Link</a>
                            <button class="btn btn-outline-danger btn-sm m-1" @click="confirmDeleteOnline(online)"><i class="bi bi-trash text-danger"></i> Delete</button>
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
        return { sharedState, settings, formatDate };
    },
    data() {
        return {
            onlines: [],
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
                url: online.url,
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
        }
    },
    mounted() {
        this.fetchOnlines();
    }
}
