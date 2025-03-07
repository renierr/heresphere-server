import {eventBus} from "event-bus";
import {apiCall, debounce, showConfirmDialog, showToast} from "helper";
import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
<footer class="footer py-3">
    <div class="text-center">
        <div class="d-grid gap-2 d-sm-flex justify-content-sm-center">
            <a v-if="updatePossible" href="#" @click.prevent="confirmUpdate" class="btn btn-danger btn-sm">Server Update</a>
            <a href="#" @click.prevent="confirmCleanup" class="btn btn-danger btn-sm">Cleanup Files</a>
            <a href="#" @click.prevent="cacheClear" class="btn btn-warning btn-sm">Clear all Caches</a>
            <a href="#" @click.prevent="scanFiles" class="btn btn-warning btn-sm">Scan Videos</a>
            <a href="#" @click.prevent="generateThumbnails" class="btn btn-secondary btn-sm">Generate Thumbnails</a>
            <a href="#" @click.prevent="fetchFiles" class="btn btn-secondary btn-sm">Reload files</a>
            <a href="#" @click.prevent="findDuplicates" class="btn btn-info btn-sm">Find Duplicates</a>
        </div>
    </div>
</footer>
`

export const PageFunctions = {
    template: template,
    props: {
        updatePossible: {
            type: Boolean,
            default: false,
        },
    },
    setup() {
        return { sharedState, settings };
    },
    data() {
        return {
            removeFetchFilesListener: null,
        }
    },
    computed: {
    },
    methods: {
        confirmUpdate() {
            const confirmData = {
                title: 'Server Update',
                message: `This will call a Server Update. The process might be killed and connection can get lost, Are you sure you want to proceed?`,
                submit: 'Update',
                action: this.updateServer,
            }
            showConfirmDialog(confirmData);
        },
        updateServer() {
            apiCall('/update', { errorMessage: 'Server may lost connection after update see Info box or reload page'})
        },
        confirmCleanup() {
            const confirmData = {
                title: 'Cleanup files',
                message: `This will clean the download tracked files and find orphan thumbnails and delete them, Are you sure you want to proceed?`,
                submit: 'Cleanup',
                action: this.cleanup,
            }
            showConfirmDialog(confirmData);
        },
        cleanup() { // Add this method
            apiCall('/cleanup', { errorMessage: 'Error occurred during cleanup' })
                .then(() => this.fetchFiles());
        },
        cacheClear() {
            apiCall('/cache/clear', { errorMessage: 'Error clearing cache' })
                .then(() => this.fetchFiles());
        },
        scanFiles() {
            apiCall('/scan', { errorMessage: 'Error scanning files'});
        },
        generateThumbnails() {
            apiCall('/api/generate_thumbnails', { errorMessage: 'Error generating thumbnails',
                showToastMessage: false, options: { method: 'POST', headers: {'Content-Type': 'application/json'} } })
                .then(data => showToast(data.success ? data : 'Failed to generate thumbnails'));
        },
        fetchFiles: debounce(function (restoreScrollPosition=false) {
            // if we are in library url path we should use library api
            const scrollPosition = window.scrollY;

            sharedState.loading = true;
            apiCall('/api/list', { errorMessage: 'Error fetching files',
                onError: () => sharedState.loading = false, showToastMessage: false })
                .then(data => {
                    sharedState.files = data.map(file => ({
                        ...file,
                        showPreview: false,
                    }));
                    sharedState.loading = false;
                    if (restoreScrollPosition) {
                        console.log('Restoring scroll position', scrollPosition);
                        setTimeout(() => window.scrollTo(0, scrollPosition));
                    }
                });
        }, 2000),
        findDuplicates() {
            sharedState.loading = true;
            apiCall('/api/duplicates', { errorMessage: 'Error finding duplicates',
                showToastMessage: false, onError: () => sharedState.loading = false })
                .then(data => {
                    sharedState.loading = false;
                    if (data.error) {
                        showToast(data.message, { title: data.error });
                    } else {
                        const output = `TODO: implement nice dialog.... found ${Object.keys(data).length} possible duplicates<br>${outputSimilarVideos(data)}`;
                        showToast(output, { stayOpen: true, asHtml: true, wide: true });
                    }
                    console.log(data);
                });
        },
    },
    beforeUnmount() {
        if (this.removeFetchFilesListener) {
            this.removeFetchFilesListener();
            this.removeFetchFilesListener = null;
        }
    },
    mounted() {
        this.removeFetchFilesListener = eventBus.on('fetch-files', (data) => {
            console.log('Fetching files with data:', data);
            this.fetchFiles(data);
        });
    }
}

function outputSimilarVideos(data) {
    let htmlOutput = '<div class="similar-videos-container">';
    for (const [videoPath, details] of Object.entries(data)) {
        htmlOutput += `<div class="video-section">
                <p>Video: ${details.file.title} [${videoPath}] has similar videos:</p>`;
        const simData = details.similar;
        if (simData) {
            htmlOutput += '<ul>';
            simData.forEach(similarVideo => {
                htmlOutput += `<li><strong>Score:</strong> ${similarVideo.score} - <strong>Similar to:</strong> ${similarVideo.file.title} [${similarVideo.video_url}]</li>`;
            });
            htmlOutput += '</ul>';
        }
        htmlOutput += '</div>';
    }
    htmlOutput += '</div>';
    return htmlOutput;
}