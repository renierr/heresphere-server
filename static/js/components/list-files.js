import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
<div v-if="filteredFiles.length === 0" class="card-body text-center">No Files present</div>
<hs-paging></hs-paging>

<div class="container file-list">
    <div class="row">
        <div v-for="file in filteredFiles" :key="file.filename" class="col-12 col-sm-6 col-md-4 col-lg-3 mb-4 position-relative">
            <hs-file-progress :file></hs-file-progress>
            <hs-video-infos-card :file></hs-video-infos-card>
        </div>
    </div>
</div>
`

import { Paging } from "./paging.js";
import { FileProgress } from "./file-progress.js";
import { VideoInfosCard } from "./video-infos-card.js";

export const ListFiles = {
    template: template,
    components: {
        'hs-paging': Paging,
        'hs-file-progress': FileProgress,
        'hs-video-infos-card': VideoInfosCard,
    },
    setup() {
        return { sharedState, settings };
    },
    computed: {
        filteredFiles: function () {

            let filtered = sharedState.files.filter(file => {
                const matchesFolder = sharedState.selectedFolder ? file.folder === sharedState.selectedFolder || (file.folder === '' && sharedState.selectedFolder === '~root~') : true;
                const titleCompareValue = (file.title || file.filename.split('/').pop().split('.').slice(0, -1).join('.')).toLowerCase();
                const matchesFilter = sharedState.filter ? titleCompareValue.includes(sharedState.filter.toLowerCase()) : true;
                const matchesResolution = sharedState.selectedResolution ? this.checkResolution(file) : true;
                const matchesDuration = sharedState.selectedDuration ? this.checkDuration(file) : true;
                return matchesFolder && matchesFilter && matchesResolution && matchesDuration;
            });

            const sortCriteria = sharedState.currentSort.split(' ');
            filtered = filtered.sort((a, b) => {
                for (let criterion of sortCriteria) {
                    let modifier = 1;
                    if (sharedState.currentSortDir === 'desc') modifier = -1;
                    if (a[criterion] < b[criterion]) return -1 * modifier;
                    if (a[criterion] > b[criterion]) return 1 * modifier;
                }
                return 0;
            });

            sharedState.totalItems = filtered.length;
            sharedState.totalSize = filtered.reduce((acc, file) => acc + (file.filesize || 0), 0);

            if (settings.pageSize === 0) {
                return filtered; // Return all items if pageSize is 0
            }
            const start = (sharedState.currentPage - 1) * settings.pageSize;
            const end = start + settings.pageSize;
            return filtered.slice(start, end);
        },
    },
    methods: {
        checkResolution(file) {
            if (sharedState.selectedResolution === 'HD') {
                return file.width > 1900 || file.height > 1900;
            } else if (this.selectedResolution === '4K') {
                return file.width >= 3800 || file.height >= 3800;
            } else if (this.selectedResolution === '8K') {
                return file.width >= 8000 || file.height >= 8000;
            }
            return true;
        },
        checkDuration(file) {
            const durationInMinutes = file.duration / 60;
            return durationInMinutes >= sharedState.selectedDuration;
        },
    }
}