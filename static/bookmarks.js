import { data, methods, computed, watch } from './common.js';

new Vue({
    el: '#app',
    data: {
        bookmarks: [],
        serverOutput: '',
        loading: false,
    },
    methods: {
        ...methods.showMessage,
    },
    computed: {
    },
    watch: {
    },
    mounted: function () {
        // fetch bookmarks
        this.loading = true;
        fetch('/api/bookmarks')
            .then(response => response.json())
            .then(data => {
                this.bookmarks = data;
                this.loading = false;
            })
            .catch(error => {
                console.error('There was an error fetching the files:', error);
                this.loading = false;
            });

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
