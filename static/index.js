import {showToast} from "helper";
import {
    data,
    methods,
    computed,
    watch,
} from './common.js';

import { createApp } from 'vue';
import { eventBus } from 'event-bus';
import { sharedState, settings } from 'shared-state';

const app = createApp({
    data() {
        return {
            ...data,
            downloadProgress: {},
            removeSseListener: null,
        }
    },
    setup() {
        return { sharedState, settings };
    },
    methods: {
        ...methods,
        redownload(file) {
            this.videoUrl = file.url;
            this.postVideoUrl();
        },
    },
    computed: {
        ...computed,
        getProgressForId: function () {
            return function (id) {
                return this.downloadProgress[id] || 0;
            };
        },
    },
    watch: {
        ...watch,
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
        window.vueInstance = this;    // store vue instance in DOM
        this.fetchFiles();
        this.removeSseListener = eventBus.on('sse-message', (data) => {
            let progressExp = data.match(/(\d+.\d+)% complete/);
            let progressId = data.match(/Downloading...\[(\d+)]/);
            if (progressId) {
                this.downloadProgress = this.downloadProgress || {};
                this.downloadProgress[progressId[1]] = progressExp ? parseFloat(progressExp[1]) : 0;
            }

            if (data.includes('Download failed')) {
                let progressId = data.match(/Download failed \[(\d+)]/);
                if (progressId) {
                    this.downloadProgress[progressId[1]] = 0;
                }
            }

            if (data.includes('Download finished') ||
              data.includes('Generate thumbnails finished') ||
              data.includes(' 0.0% complete')) {
                this.fetchFiles();
            }
        });
    },
});

app.config.errorHandler = function (err, instance, info) {
    // Log the error details to the console
    console.error(`Error: ${err.toString()}\nInfo: ${info}`);
    showToast(err.toString(), { title: 'An error occurred', stayOpen: true });
};

import { ServerInfo } from './js/components/server-info.js';
import { Filter } from './js/components/filter.js';
import { Paging } from "./js/components/paging.js";
import { Loading } from "./js/components/loading.js";
import { ToastMessage } from "./js/components/toast-message.js";
import { VideoUrl } from "./js/components/video-url.js";

app.component('hs-server-info', ServerInfo);
app.component('hs-filter', Filter);
app.component('hs-paging', Paging);
app.component('hs-loading', Loading);
app.component('hs-video-url', VideoUrl);
app.component('hs-toast', ToastMessage);
app.mount('#app');

