import {eventBus} from "event-bus";
import { sharedState, settings } from "shared-state";
import {formatFileSize, formatDate, formatDuration, playVideo, apiCall, videoUrl} from "helper";
import {confirmMoveFile, confirmDeleteFile, confirmRenameFile, showDuplicateInfo} from "../helpers/video-actions.js";

// language=Vue
const template = `
<div ref="videoDetailsModal" class="modal fade" id="videoDetailsModal" tabindex="-1">
    <div class="modal-dialog modal-lg modal-fullscreen-lg-down modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title text-truncate" id="videoDetailsModalLabel">{{ currentFile ? currentFile.title :
                    'Video Details' }}</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div v-if="currentFile" class="modal-body">
                <div class="w-100 d-flex flex-column flex-sm-row gap-2 align-items-start pt-3 p-2">
                    <img v-if="currentFile.thumbnail" tabindex="0" :src="currentFile.thumbnail" alt="Thumbnail"
                         class="similar-thumbnail p-2 border border-secondary-subtle border-2 text-center">
                    <div class="text-muted">
                        <p>
                            <span v-if="currentFile.filesize"><i class="bi bi-asterisk"></i> {{ formatFileSize(currentFile.filesize) }}&nbsp;</span>
                            <span v-if="currentFile.width && currentFile.height">&nbsp;<i class="bi bi-aspect-ratio"></i> {{ currentFile.width }}x{{ currentFile.height}}&nbsp;</span>
                            <span v-if="currentFile.width && (currentFile.width > 1900 || currentFile.height > 1900)">
                              &nbsp;<i class="bi bi-badge-hd-fill"></i></span>
                            <span v-if="currentFile.width && (currentFile.width >= 8000 || currentFile.height >= 8000)">
                              &nbsp;<i class="bi bi-badge-8k-fill"></i></span>
                            <span v-else-if="currentFile.width && (currentFile.width > 3800 || currentFile.height > 3800)">
                              &nbsp;<i class="bi bi-badge-4k-fill"></i></span>
                            <span v-if="currentFile.stereo">&nbsp;<i class="bi bi-badge-3d-fill"></i></span>
                        </p>
                        <p><i class="bi bi-calendar"></i> {{ formatDate(currentFile.created) }} (Created)</p>
                        <p v-if="currentFile.download_date"><i class="bi bi-calendar-check"></i> {{
                            formatDate(currentFile.download_date) }} (Downloaded)</p>
                        <p v-if="currentFile.duration"><i class="bi bi-clock"></i> {{
                            formatDuration(currentFile.duration) }}</p>
                        <p v-if="currentFile.folder"><i class="bi bi-folder"></i> {{ currentFile.folder }}</p>
                        <div v-if="currentFile.may_exist" @click.stop.prevent="showDuplicateInfo(currentFile)"
                             class="exists d-inline-block p-2 mt-2 w-100 text-center text-bg-warning rounded cursor-pointer"
                             style="word-break: break-word">Possible duplicate file
                        </div>
                        <div class="mt-2 pt-1 d-flex flex-wrap gap-2">
                            <button class="btn btn-outline-success btn-sm m-1" @click="playVideo(currentFile)"><i
                                class="bi bi-play-fill"></i>&nbsp;Play
                            </button>
                            <div class="btn-group" role="group">
                                <button type="button" class="btn btn-outline-secondary btn-sm m-1 dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
                                  <i class="bi bi-gear-fill"></i> Actions
                                </button>
                                <ul class="dropdown-menu">
                                  <li><button v-if="currentFile.title" class="dropdown-item" @click="filterFile(currentFile)"><i class="bi bi-funnel text-secondary"></i> Filter File</button></li>  
                                  <li><button v-if="currentFile.url" class="dropdown-item" @click="videoUrl(currentFile.url)"><i class="bi bi-repeat text-secondary"></i> Download again</button></li>
                                  <li><button v-if="!currentFile.partial && !currentFile.unknown" class="dropdown-item" @click="confirmRenameFile(currentFile)"><i class="bi bi-pencil-square text-warning"></i> Rename</button></li>
                                  <li><button class="dropdown-item" @click="confirmMoveFile(currentFile)"><i class="bi bi-folder text-danger"></i> Move To Folder</button></li>
                                  <li><button class="dropdown-item" @click="confirmDeleteFile(currentFile.filename)"><i class="bi bi-trash text-danger"></i> Delete</button></li>
                                </ul>
                            </div>
                            <a v-if="currentFile.url" class="btn btn-outline-secondary btn-sm m-1" :href="currentFile.url" target="_blank"><i class="bi bi-link"></i> Original Link</a>
                        </div>
                    </div>
                </div>
                <div v-if="similarVideos !== null">
                    <hr>
                    <p>Found {{ similarVideos?.length }} similar videos (limit to: 10)</p>
                    <ul v-if="similarVideos?.length" class="list-unstyled">
                        <li v-for="similar in similarVideos" class="mb-2">
                            <p class="text-muted text-wrap m-0" style="word-break: break-word;"><span class="score fw-bold">({{ similar.score }} %)</span>
                                - {{ similar.file?.title }}</p>
                            <div v-if="currentFile.uid === similar.file?.uid" class="alert alert-warning m-1 p-2">
                                <strong>Warning!</strong> This file is the same as the current file.
                            </div>

                            <div v-if="similar.file" class="w-100 d-flex flex-column flex-sm-row gap-2 align-items-start pt-3 p-2">
                                <img :src="similar.file.thumbnail" tabindex="0" alt="Thumbnail"
                                     class="similar-thumbnail p-2 border border-secondary-subtle border-2 text-center"/>
                                <div class="text-muted">
                                    <p v-if="similar.file.filesize"><i class="bi bi-asterisk"></i> {{ formatFileSize(similar.file.filesize) }}
                                        <span v-if="similar.file.width && similar.file.height"><i class="bi bi-aspect-ratio"></i> {{ similar.file.width }}x{{ similar.file.height}}&nbsp;</span>
                                        <span v-if="similar.file.stereo">&nbsp;<i class="bi bi-badge-3d-fill"></i></span>
                                    </p>
                                    <p><i class="bi bi-calendar"></i> {{ formatDate(similar.file.created) }} (Created)</p>
                                    <p v-if="similar.file.download_date"><i class="bi bi-calendar-check"></i> {{
                                        formatDate(similar.file.download_date) }} (Downloaded)</p>
                                    <p v-if="similar.file.duration"><i class="bi bi-clock"></i> {{
                                        formatDuration(similar.file.duration) }}</p>
                                    <p v-if="similar.file.folder"><i class="bi bi-folder"></i> {{ similar.file.folder }}</p>
                                    <div class="d-flex flex-wrap gap-1 mt-2">
                                        <button class="btn btn-outline-success btn-sm m-1" @click="playVideo(similar.file)">
                                            <i class="bi bi-play-fill"></i>&nbsp;Play
                                        </button>
                                        <div class="btn-group" role="group">
                                            <button type="button" class="btn btn-outline-secondary btn-sm m-1 dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
                                              <i class="bi bi-gear-fill"></i> Actions
                                            </button>
                                            <ul class="dropdown-menu">
                                              <li><button v-if="similar.file.title" class="dropdown-item" @click="filterFile(similar.file)"><i class="bi bi-funnel text-secondary"></i> Filter File</button></li>
                                              <li><button v-if="!similar.file.partial && !similar.file.unknown" class="dropdown-item" @click="confirmRenameFile(similar.file)"><i class="bi bi-pencil-square text-warning"></i> Rename</button></li>
                                              <li><button class="dropdown-item" @click="confirmMoveFile(similar.file)"><i class="bi bi-folder text-danger"></i> Move To Folder</button></li>
                                              <li><button class="dropdown-item" @click="confirmDeleteFile(similar.file.filename)"><i class="bi bi-trash text-danger"></i> Delete</button></li>
                                            </ul>
                                        </div>
                                        <button @click="showDetails(similar.file)" class="btn btn-outline-info btn-sm m-1"><i class="bi bi-eye"></i> Show Similar</button>
                                    </div>
                                </div>
                            </div>
                        </li>
                    </ul>
                </div>
                <div v-else class="d-flex flex-row justify-content-center align-items-center gap-4 pt-2">
                    <span>Loading similar Videos...</span>
                    <div class="spinner-border" role="status"></div>
                </div>
            </div>
            <div v-else class="modal-body">
                <p>No file selected</p>
            </div>
        </div>
    </div>
</div>
`

export const VideoDetails = {
    template: template,
    setup() {
        return { sharedState, settings, formatFileSize, formatDate, formatDuration, playVideo, videoUrl};
    },
    data() {
        return {
            modal: null,
            listener: [],
            currentFile: null,
            similarVideos: null,
        }
    },
    methods: {
        filterFile(file) {
            sharedState.filter = file.title;
            settings.filterAccordionOpen = true;
        },
        showDetails(file) {
            this.similarVideos = null;
            this.currentFile = file;
            // TODO maybe better in mounted or setup?
            const videoElement = this.$refs.videoDetailsModal;
            if (!this.modal) {
                this.modal = new bootstrap.Modal(videoElement, { backdrop: 'static' });
                videoElement.addEventListener('hidden.bs.modal', () => {
                    this.currentFile = null;
                });
            }
            this.modal.show();

            // load similar videos
            const post_options = {
                method: 'POST',
                body: JSON.stringify({ video_path: file.filename, threshold: settings.similarThreshold }),
                headers: { 'Content-Type': 'application/json' }
            };
            apiCall('/api/similar', { errorMessage: 'Error loading similar videos',
                showToastMessage: false,
                options: post_options })
                .then(data => {
                    this.similarVideos = data;
                });
        },
        showDuplicateInfo,
        confirmMoveFile,
        confirmDeleteFile,
        confirmRenameFile,
    },
    beforeUnmount() {
        this.listener.forEach(l => l());
        this.modal = null;
    },
    mounted() {
        this.listener.push(eventBus.on('video-details', (file) => {
            this.showDetails(file);
        }));

    }
}
