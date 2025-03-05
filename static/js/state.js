import { reactive } from 'vue';

export const sharedState = reactive({
    files: [],
    filter: '',
    selectedFolder: '',
    selectedResolution: '',
    selectedDuration: 0,
    currentSort: 'created',
    currentSortDir: 'desc',
});
