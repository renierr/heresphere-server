import { sharedState, settings } from "shared-state";
import { fetchFiles, playVideo, showToast } from "helper";
import { createApp } from 'vue';
import { eventBus } from 'event-bus';

const app = createApp({
    data() {
        return {
            removeSseListener: null,
        }
    },
    setup() {
        return { sharedState, settings, playVideo };
    },
    methods: {
        saveSettings() {
            localStorage.setItem('settings', JSON.stringify(this.settings));
        },
        handleViewChange(view) {
            sharedState.currentView = view;
            history.replaceState(null, '', view ? `/${view}` : '/');
        },
    },
    computed: {
        isActive() {
            return (view) => {
                return sharedState.currentView === view ? 'active fw-bold' : '';
            };
        }
    },
    watch: {
        'sharedState.filter': function (newFilter, oldFilter) {
            sharedState.currentPage = 1;
        },
        'settings.pageSize': function (newPageSize, oldPageSize) {
            sharedState.currentPage = 1;
        },
        'sharedState.selectedFolder': function (newFolder, oldFolder) {
            sharedState.currentPage = 1;
        },
        settings: {
            handler() {
                this.saveSettings()
            },
            deep: true,
        }
    },
    beforeUnmount() {
        if (this.removeSseListener) {
            this.removeSseListener();
        }
        eventBus.events = {};
    },
    mounted() {
        const path = window.location.pathname.replace('/', '');
        sharedState.currentView = path || '';
        fetchFiles();
        this.removeSseListener = eventBus.on('sse-message', (data) => {
            // ignore messages starting with " - ", because they belong to last message output
            if (data.startsWith(' - ')) {
                return;
            }
            let progressExp = data.match(/(\d+.\d+)% complete/);
            let progressId = data.match(/Downloading...\[(\d+)]/);
            if (progressId) {
                sharedState.downloadProgress = sharedState.downloadProgress || {};
                sharedState.downloadProgress[progressId[1]] = progressExp ? parseFloat(progressExp[1]) : 0;
            }

            if (data.includes('Download failed')) {
                let progressId = data.match(/Download failed \[(\d+)]/);
                if (progressId) {
                    sharedState.downloadProgress[progressId[1]] = 0;
                }
            }

            if (data.includes('Download finished') ||
              data.includes('Generate thumbnails finished') ||
              data.includes(' 0.0% complete')) {
                fetchFiles();
            }
        });
    },
});

app.config.errorHandler = function (err, instance, info) {
    // Log the error details to the console
    console.error(`Error: ${err.toString()}\nInfo: ${info}`);
    showToast(err.toString(), { title: 'An error occurred', stayOpen: true });
};

import { ServerInfo } from './components/server-info.js';
import { Filter } from './components/filter.js';
import { Loading } from "./components/loading.js";
import { ToastMessage } from "./components/toast-message.js";
import { VideoPlayer } from "./components/video-player.js";
import { VideoUrl } from "./components/video-url.js";
import { PageFunctions } from "./components/page-functions.js";
import { ConfirmDialog } from "./components/confirm-dialog.js";
import { ListFiles } from "./components/list-files.js";
import { VideoDetails } from "./components/video-details.js";
import { Bookmarks } from "./components/bookmarks.js";
import { ScrollTop } from "./components/scroll-top.js";
import { DarkMode } from "./components/dark-mode.js";
import { Mosaic } from "./components/mosaic.js"
import { Online } from "./components/online.js"

app.component('hs-server-info', ServerInfo);
app.component('hs-filter', Filter);
app.component('hs-loading', Loading);
app.component('hs-video-url', VideoUrl);
app.component('hs-toast', ToastMessage);
app.component('hs-page-functions', PageFunctions);
app.component('hs-confirm-dialog', ConfirmDialog);
app.component('hs-video-player', VideoPlayer);
app.component('hs-list-files', ListFiles);
app.component('hs-video-details', VideoDetails);
app.component('hs-bookmarks', Bookmarks);
app.component('hs-scroll-top', ScrollTop);
app.component('hs-dark-mode', DarkMode);
app.component('hs-mosaic', Mosaic);
app.component('hs-online', Online);

app.mount('#app');

