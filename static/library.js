import {
    data,
    methods,
    computed,
    watch,
    addSwipeNavigationForPagingListener, addKeyNavigationForPagingListener, removeKeyNavigationForPagingListener
} from './common.js';

new Vue({
    el: '#app',
    data: {
        ...data,
    },
    methods: {
        ...methods,
    },
    computed: {
        ...computed,
    },
    watch: {
        ...watch,
    },
    beforeDestroy() {
        removeKeyNavigationForPagingListener();
    },
    mounted: function () {
        window.vueInstance = this;    // store vue instance in DOM
        addKeyNavigationForPagingListener(this);
        addSwipeNavigationForPagingListener(this);
        this.fetchFiles();
        const eventSource = new EventSource('/sse');
        const serverOutput = [];
        eventSource.onmessage = event => {
            serverOutput.push(new Date().toLocaleTimeString() + ': ' + event.data);
            if (serverOutput.length > 100) {
                serverOutput.shift();
            }
            this.serverOutput = serverOutput.slice().reverse().join('\n');
            if (event.data.includes('Generate thumbnails finished')) {
                this.fetchFiles();
            }
        };
    }
});
