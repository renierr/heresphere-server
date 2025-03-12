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
    hideConfirmDialog
} from "helper";

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
        <div class="icon-overlay position-absolute bottom-0 end-0 pe-1 ps-1 text-secondary fs-3 lh-1 rounded">
            <span v-if="file.width && (file.width > 1900 || file.height > 1900)"><i class="bi bi-badge-hd-fill"></i></span>
            <span v-if="file.width && (file.width >= 8000 || file.height >= 8000)"><i class="bi bi-badge-8k-fill"></i></span>
            <span v-else-if="file.width && (file.width > 3800 || file.height > 3800)"><i class="bi bi-badge-4k-fill"></i></span>
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
            <span v-if="file.duration"><i class="bi bi-clock"></i> {{ formatDuration(file.duration) }}&nbsp;</span>
            <span v-if="file.width && file.height"><i class="bi bi-aspect-ratio"></i> {{ file.width }}x{{ file.height}}</span>
        </p>
        <p class="mb-0">
            <span v-if="file.filesize"><i class="bi bi-asterisk"></i> {{ formatFileSize(file.filesize) }}&nbsp;</span>
            <span v-if="file.folder" class="mb-0"><i class="bi bi-folder"></i> {{ file.folder }}</span>
        </p>
        <p v-if="file.unknown" class="mb-0"><span v-if="file.mimetype"><i class="bi bi-braces"></i> {{ file.mimetype }}</span></p>
    </div>
    <div class="card-footer p-2 d-flex flex-wrap gap-2">
        <button v-if="!file.unknown" class="btn btn-outline-success btn-sm" @click="playVideo(file)">
            <i class="bi bi-play-fill"></i> Play
        </button>
        <button v-if="!file.partial && !file.unknown" class="btn btn-outline-secondary btn-sm" @click="generateThumbnail(file.filename)">Generate Thumbnail</button>
        <button v-if="!file.partial && !file.unknown" class="btn btn-outline-warning btn-sm" @click="confirmRenameFile(file)">Rename</button>
        <button @click="confirmDeleteFile(file.filename)" class="btn btn-outline-danger btn-sm">Delete</button>
        <button @click="confirmMoveFile(file)" class="btn btn-outline-danger btn-sm">Move To Folder</button>
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
        return { sharedState, settings, formatDuration, formatFileSize, playVideo };
    },
    methods: {
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
        showDuplicateInfo(file) {
            if (file.may_exist) {
                let message = file.may_exist.split('\n');
                message = message.map((line) => {
                    if (line.includes('id[')) {
                        return `<h5>${line}</h5>`
                    } else {
                        return `<p>${line}</p>`;
                    }
                }).join('<br>');
                showToast(message, {title: "Duplicates", stayOpen: true, asHtml: true, wide: true});
            }
        },
        generateThumbnail(file) {
            apiCall('/api/generate_thumbnail', { errorMessage: 'Error generating thumbnail',
                showToastMessage: false,
                options: { method: 'POST', body: JSON.stringify({ video_path: file }), headers: {'Content-Type': 'application/json'} } })
                .then(data => showToast(data.success ? data : 'Failed to generate thumbnail'));
        },
        showVideoDetails(file) {
            eventBus.emit('video-details', file);
        },
        confirmDeleteFile(filename) {
            const confirmData = {
                title: 'Delete file',
                message: `Are you sure you want to delete the following file?`,
                file: filename,
                submit: 'Delete',
                action: this.deleteFile,
            }
            showConfirmDialog(confirmData);
        },
        deleteFile(confData) {
            if (!confData && !confData.file) {
                showToast('Wrong number of parameters for deleteFile');
                return;
            }
            const file = confData.file;
            const utf8Bytes = new TextEncoder().encode(file);
            const encodedUrl = btoa(String.fromCharCode(...utf8Bytes));
            const deleteOptions =
            apiCall(`/api/files?url=${encodeURIComponent(encodedUrl)}`, { errorMessage: 'Error deleting file',
                options: { method: 'DELETE'} })
                .then(data => {
                    fetchFiles(true);
                });
        },
        confirmRenameFile(file) {
            const modalConfirmExtras = document.getElementById('confirmModalExtras'); // TODO implement extras handling
            const currentName = file.title || file.filename.split('/').pop().split('.').slice(0, -1).join('.');;
            modalConfirmExtras.innerHTML = `
            <div class="d-flex align-items-center flex-column flex-md-row">
                <input id="confModal_fileName" class="form-control" type="text" />
            </div>
            `;
            const nameInput = document.getElementById('confModal_fileName');
            nameInput.value = currentName;
            const confirmData = {
                title: 'Rename file',
                message: `Rename the title for the following file:`,
                file: file.filename,
                submit: 'Rename',
                action: (confData) => {
                    let newName = nameInput.value;
                    if (newName === currentName) {
                        showToast('New name is the same as the current name');
                        return;
                    }
                    this.renameFile(confData, newName);
                },
            }
            showConfirmDialog(confirmData);
            nameInput.addEventListener('keydown', (evt) => {
                if (evt.key === 'Enter') {
                    evt.preventDefault();
                    hideConfirmDialog();
                    confirmData.action(confirmData)
                }
            });

        },
        renameFile(confData, newName) {
            if (!confData && !confData.file) {
                showToast('Wrong number of parameters for move to library');
                return;
            }
            const file = confData.file;
            const postOptions = {
                method: 'POST',
                body: JSON.stringify({ video_path: file, newName: newName }),
                headers: { 'Content-Type': 'application/json' }
            };
            apiCall('/api/rename', { errorMessage: 'Error renaming file',
                options: postOptions })
                .then(data => {
                    fetchFiles(true);
                });
        },
        confirmMoveFile(file) {
            const lastFolder = settings.lastMoveSubfolder || '';
            const modalConfirmExtras = document.getElementById('confirmModalExtras');
            const options = library_subfolders.map(subfolder => {
                const selected = subfolder === lastFolder ? 'selected' : '';
                return `<option value="${subfolder}" ${selected}>${subfolder}</option>`;
            }).join('');
            modalConfirmExtras.innerHTML = `
            <div class="d-flex align-items-center flex-column flex-md-row">
                <label for="subfolderSelect" class="form-label me-2 text-nowrap">Target Subfolder</label>
                <select id="subfolderSelect" class="form-select">
                    <option value="">Move to library root folder</option>
                    <option value="~videos~">Move to videos folder</option>
                    ${options}
                </select>
            </div>
            `;
            const confirmData = {
                title: 'Move file',
                message: `Are you sure you want to move the following file inside library?`,
                file: file.filename,
                submit: 'Move',
                action: (confData) => {
                    let subfolderSelection = document.getElementById('subfolderSelect').value;
                    if (file.folder === subfolderSelection) {
                        showToast('Cannot move file inside its own folder');
                        return;
                    }
                    this.moveFile(confData, subfolderSelection);
                },
            }
            showConfirmDialog(confirmData);
        },
        moveFile(confData, subfolder) {
            if (!confData && !confData.file) {
                showToast('Wrong number of parameters for move to library');
                return;
            }
            const file = confData.file;
            settings.lastMoveSubfolder = subfolder;
            const postOptions = {
                method: 'POST',
                body: JSON.stringify({ video_path: file, subfolder: subfolder }),
                headers: { 'Content-Type': 'application/json' }
            };
            apiCall('/api/move_file', { errorMessage: 'Error moving file',
                options: postOptions })
                .then(data => {
                    fetchFiles(true);
                });
        },
    }
}