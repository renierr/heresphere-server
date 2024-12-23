import { data, methods, computed, watch } from './common.js';

new Vue({
    el: '#app',
    data: {
        serverOutput: '',
    },
    methods: {
    },
    computed: {
    },
    watch: {
    },
    mounted: function () {
        // fetch bookmarks

        const eventSource = new EventSource('/sse');
        const serverOutput = [];
        eventSource.onmessage = event => {
            serverOutput.push(new Date().toLocaleTimeString() + ': ' + event.data);
            if (serverOutput.length > 100) {
                serverOutput.shift();
            }
            this.serverOutput = serverOutput.slice().reverse().join('\n');
        };
    }
});
