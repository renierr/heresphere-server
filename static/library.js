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
        this.openAndHandleSSEConnection((evt) => {
            if (evt.data.includes('Generate thumbnails finished')) {
                this.fetchFiles();
            }
        });
    }
});
