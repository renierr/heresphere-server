import {eventBus} from "event-bus";
import { sharedState, settings } from "shared-state";
import {
    apiCall,
    formatDuration,
    formatFileSize,
    showToast,
    playVideo,
    fetchFiles,
    showConfirmDialog,
    hideConfirmDialog,
    videoUrl, handleViewChange
} from "helper";
import {confirmDeleteFile, confirmRenameFile, confirmMoveFile, generateThumbnail, showDuplicateInfo} from "../helpers/video-actions.js";

// language=Vue
const template = `
<div class="card h-100 d-flex flex-column">
    <div class="thumbnail-wrapper position-relative w-100 cursor-pointer" @click="showVideoDetails(file)">
        <video v-if="settings.showVideoPreview && file.preview" :poster="file.thumbnail" :src="file.preview" class="card-img-top"
               @mouseenter="startPreview(file, $event)" @mouseleave="stopPreview(file, $event)"
               preload="none" loop disablePictureInPicture></video>
        <img v-else-if="file.thumbnail" :src="file.thumbnail" class="card-img-top" />
        <span v-if="file.showPreview" class="video-preview-indicator text-primary fs-3">
        <i class="bi bi-play-circle-fill"></i>
    </span>
        <span v-if="file.partial" class="position-absolute text-danger h3" style="left: .5rem; top: 1rem; text-shadow: 2px 2px rgba(0, 0, 0, .3);"><i class="bi bi-exclamation-circle-fill partial-icon"></i>  Partial <span class="fs-6">({{file.download_id}})</span><span v-if="file.failed"> - failed</span></span>
        <span v-if="file.unknown" class="position-absolute text-warning h3" style="left: .5rem; top: 1rem; text-shadow: 2px 2px rgba(0, 0, 0, .3);"><i class="bi bi-exclamation-circle-fill partial-icon"></i>  Not a Video</span>
        <span v-if="file.may_exist" :title="'Possible duplicate file: ' + file.may_exist" @click.stop.prevent="showDuplicateInfo(file)" class="position-absolute text-warning h3" style="left: 0.5rem; top: 3rem; text-shadow: 2px 2px rgba(0, 0, 0, .3);"><i class="bi bi-exclamation-triangle-fill exist-icon"></i> Duplicate?</span>
        <div class="icon-overlay position-absolute bottom-0 end-0 pe-1 ps-1 text-info fs-3 lh-1 rounded">
            <span v-if="file.stereo"><i class="bi bi-badge-3d-fill"></i></span>
        </div>
        <div v-if="!file.partial" class="icon-overlay position-absolute top-0 end-0 text-primary fs-3 lh-1 rounded" data-bs-toggle="tooltip" title="Toggle Favorite">
            <span @click.stop.prevent="toggleFavorite(file)"><i v-if="file.favorite" class="link-warning bi bi-star-fill"></i><i v-else class="bi bi-star"></i></span>
        </div>
    </div>
    <div class="card-body flex-grow-1">
        <h5 class="card-title text-truncate" data-bs-toggle="tooltip" :title="file.title">
            <a class="video-link text-decoration-none" :href="file.filename">
                <i class="bi bi-link-45deg"></i>&nbsp;{{ file.title }}
            </a>
        </h5>
        <p class="mb-0">
            <span v-if="file.duration" class="text-nowrap me-2"><i class="bi bi-clock"></i> {{ formatDuration(file.duration) }}</span>
            <span v-if="file.width && file.height" class="text-nowrap">
                <span v-if="(file.width <= 1900 && file.height <= 1900)" class="me-1"><i class="bi bi-aspect-ratio"></i></span>
                <span v-if="(file.width > 1900 || file.height > 1900)" class="me-1"><i class="bi bi-badge-hd-fill"></i></span>
                <span v-if="(file.width >= 8000 || file.height >= 8000)" class="me-1"><i class="bi bi-badge-8k-fill"></i></span>
                <span v-else-if="(file.width > 3800 || file.height > 3800)" class="me-1"><i class="bi bi-badge-4k-fill"></i></span>
                <span class="me-1">{{ file.width }}x{{ file.height}}</span>
            </span>
        </p>
        <p class="mb-0">
            <span v-if="file.filesize" class="text-nowrap me-2"><i class="bi bi-asterisk"></i> {{ formatFileSize(file.filesize) }}</span>
            <span v-if="file.folder" class="mb-0 text-nowrap me-2"><i class="bi bi-folder"></i> {{ file.folder }}</span>
        </p>
        <p v-if="file.unknown" class="mb-0"><span v-if="file.mimetype"><i class="bi bi-braces"></i> {{ file.mimetype }}</span></p>
    </div>
    <div class="card-footer p-2 d-flex flex-wrap gap-2">
        <button v-if="!file.unknown" class="btn btn-outline-success btn-sm" @click="playVideo(file)">
            <i class="bi bi-play-fill"></i> Play
        </button>
        <div class="btn-group" role="group">
            <button type="button" class="btn btn-outline-secondary btn-sm dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
              <i class="bi bi-gear-fill"></i> Actions
            </button>
            <ul class="dropdown-menu">
                <li><button v-if="file.title" class="dropdown-item" @click="filterFile(file)"><i class="bi bi-funnel text-secondary"></i> Filter File</button></li>
                <li><a v-if="file.url" class="dropdown-item" :href="file.url" target="_blank"><i class="bi bi-link text-secondary"></i> Original Link</a></li>  
                <li><button v-if="file.url" class="dropdown-item" @click="videoUrl(file.url)"><i class="bi bi-repeat text-secondary"></i> Download again</button></li>
                <li><button v-if="!file.partial && !file.unknown" class="dropdown-item" @click="generateThumbnail(file.filename)"><i class="bi bi-image text-warning"></i> Generate Thumbnail</button></li>
                <li><button v-if="!file.partial && !file.unknown" class="dropdown-item" @click="confirmRenameFile(file)"><i class="bi bi-pencil-square text-warning"></i> Rename</button></li>
                <li><button class="dropdown-item" @click="confirmMoveFile(file)"><i class="bi bi-folder text-danger"></i> Move To Folder</button></li>
                <li><button class="dropdown-item" @click="confirmDeleteFile(file.filename)"><i class="bi bi-trash text-danger"></i> Delete</button></li>
            </ul>
        </div>
    </div>
</div>
`

let previewVideoWarningAlreadyShown = false;
export const VideoInfosCard = {
    template: template,
    props: {
        file: Object,
    },
    setup() {
        return { sharedState, settings, formatDuration, formatFileSize, playVideo, videoUrl };
    },
    methods: {
        filterFile(file) {
            sharedState.filter = file.title;
            settings.filterAccordionOpen = true;
        },
        startPreview(file, evt) {
            evt.target.play()
                .then(() => file.showPreview = true)
                .catch(error => {
                    if (error.name === 'NotAllowedError' && !previewVideoWarningAlreadyShown) {
                        showToast('Please interact with the document (e.g., click or press a key) before video preview playing is allowed.');
                        previewVideoWarningAlreadyShown = true;
                    }
                });
        },
        stopPreview(file, evt) {
            evt.target.currentTime = 0;
            evt.target.pause();
            file.showPreview = false;
        },
        toggleFavorite(file) {
            apiCall('/api/toggle_favorite', { errorMessage: 'Error favorite toggle',
                options: { method: 'POST', body: JSON.stringify({ video_path: file.filename }), headers: { 'Content-Type': 'application/json' } } })
                .then(data => {
                    file.favorite = !file.favorite;
                });
        },
        showVideoDetails(file) {
            eventBus.emit('video-details', file);
        },
        showDuplicateInfo,
        generateThumbnail,
        confirmDeleteFile,
        confirmRenameFile,
        confirmMoveFile,
    }
}