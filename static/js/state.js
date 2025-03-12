import { reactive } from 'vue';

function localStoreSettingsLoading() {
    const defaults = { pageSize: 12, filterAccordionOpen: true, infoAccordionOpen: true,
        lastMoveSubfolder: '', showVideoPreview: true, similarThreshold: 50 };
    let storedSetting = JSON.parse(localStorage.getItem('settings')) || {};
    storedSetting = {...defaults, ...storedSetting};
    return storedSetting;
}

export const sharedState = reactive({
    files: [],
    filter: '',
    selectedFolder: '',
    selectedResolution: '',
    selectedDuration: 0,
    currentSort: 'created',
    currentSortDir: 'desc',
    currentPage: 1,
    totalItems: 0,
    totalSize: 0,
    loading: false,
    downloadProgress: {},
    currentView: '',
});

export const settings = reactive({
    ...localStoreSettingsLoading(),
});
