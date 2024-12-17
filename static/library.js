import { data, methods, computed } from './common.js';

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
    mounted: function () {
        this.fetchFiles(true);
        const eventSource = new EventSource('/sse');
        const serverOutput = [];
        eventSource.onmessage = event => {
            serverOutput.push(new Date().toLocaleTimeString() + ': ' + event.data);
            if (serverOutput.length > 100) {
                serverOutput.shift();
            }
            this.serverOutput = serverOutput.slice().reverse().join('\n');
            if (event.data.includes('Generated thumbnails finished')) {
                this.fetchFiles(true);
            }
        };
    }
});
