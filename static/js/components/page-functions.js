import {apiCall, showConfirmDialog, showToast} from "helper";
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
                .then((data) => showToast(data.success ? data : 'Failed to generate thumbnails'));
        },
        fetchFiles() {
        },
        findDuplicates() {
        },
    },
    mounted() {
    }
}