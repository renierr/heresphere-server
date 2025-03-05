import { reactive } from 'vue';

function localStoreSettingsLoading() {
    const defaults = { cardLayout: true, pageSize: 12,
        filterAccordionOpen: true, infoAccordionOpen: true, lastMoveSubfolder: '', showVideoPreview: true, similarThreshold: 50 };
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
});

export const settings = reactive({
    ...localStoreSettingsLoading(),
});
