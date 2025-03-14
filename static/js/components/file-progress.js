import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
    <div v-if="getProgressForId(file.download_id) > 0" class="progress position-absolute z-1" style="width: calc(100% - 1.5rem)">
        <div class="progress-bar overflow-visible" role="progressbar" :style="{ width: getProgressForId(file.download_id) + '%' }" :aria-valuenow="getProgressForId(file.download_id)" aria-valuemin="0" aria-valuemax="100">{{ getProgressForId(file.download_id) }}%</div>
    </div>
`

export const FileProgress = {
    template: template,
    props: {
        file: Object,
    },
    setup() {
        return { sharedState, settings };
    },
    computed: {
        getProgressForId: function () {
            return function (id) {
                return sharedState.downloadProgress[id] || 0;
            };
        },
    }
}