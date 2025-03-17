import {sharedState, settings} from "shared-state";
import {formatFileSize} from "helper";

// language=Vue
const template = `
<div class="pagination mb-4 d-flex flex-column flex-md-row align-items-center justify-content-between">
    <ul v-if="totalPages > 1" class="pagination mb-0">
        <li class="page-item" :class="{ disabled: sharedState.currentPage === 1 }">
            <a class="page-link" href="#" @click.prevent="changePage(1)">First</a>
        </li>
        <li class="page-item" :class="{ disabled: sharedState.currentPage === 1 }">
            <a class="page-link" href="#" @click.prevent="changePage(sharedState.currentPage - 1)">Previous</a>
        </li>
        <li v-if="pagesToShow[0] > 1" class="page-item disabled d-none d-sm-block">
            <span class="page-link">...</span>
        </li>
        <li v-for="page in pagesToShow" :key="page" class="page-item d-none d-sm-block"
            :class="{ active: sharedState.currentPage === page }">
            <a class="page-link" href="#" @click.prevent="changePage(page)">{{ page }}</a>
        </li>
        <li v-if="pagesToShow[pagesToShow.length - 1] < totalPages" class="page-item disabled d-none d-sm-block">
            <span class="page-link">...</span>
        </li>
        <li class="page-item" :class="{ disabled: sharedState.currentPage === totalPages }">
            <a class="page-link" href="#" @click.prevent="changePage(sharedState.currentPage + 1)">Next</a>
        </li>
        <li class="page-item" :class="{ disabled: sharedState.currentPage === totalPages }">
            <a class="page-link" href="#" @click.prevent="changePage(totalPages)">Last</a>
        </li>
    </ul>
    <span v-if="totalPages > 1" class="p-2">Page {{ sharedState.currentPage }}&nbsp;/&nbsp;{{ totalPages }}</span>
    <span class="p-2">Items&nbsp;total {{ sharedState.totalItems }}&nbsp; Size&nbsp;{{ formattedTotalSize }} </span>
</div>
`

function totalPagesGlobal() {
    if (settings.pageSize === 0) return 1;
    return Math.ceil(sharedState.totalItems / settings.pageSize);
}

export function changePage(page) {
    const totalPages = totalPagesGlobal();
    if (page < 1) {
        sharedState.currentPage = 1;
    } else if (page > totalPages) {
        sharedState.currentPage = totalPages;
    } else {
        sharedState.currentPage = page;
    }
}

export const Paging = {
    template: template,
    setup() {
        return {sharedState, settings, changePage};
    },
    computed: {
        totalPages() {
            return totalPagesGlobal();
        },
        pagesToShow() {
            const range = 5;
            let start = Math.max(1, sharedState.currentPage - Math.floor(range / 2));
            let end = Math.min(this.totalPages, start + range - 1);

            if (end - start < range - 1) {
                start = Math.max(1, end - range + 1);
            }

            const pages = [];
            for (let i = start; i <= end; i++) {
                pages.push(i);
            }
            return pages;
        },
        formattedTotalSize() {
            return formatFileSize(sharedState.totalSize);
        },
    },
    beforeUnmount() {
        removeKeyNavigationForPagingListener();
        removeSwipeNavigationForPagingListener();
    },
    mounted() {
        addSwipeNavigationForPagingListener();
        addKeyNavigationForPagingListener();
    },
}

function keyNavigationForPaging(event) {
    // check if currently an input is focused
    if (document.activeElement.tagName === 'INPUT' || document.querySelector('.modal.show')) return;

    if (event.key === 'ArrowLeft') {
        changePage(sharedState.currentPage - 1);
    } else if (event.key === 'ArrowRight') {
        changePage(sharedState.currentPage + 1);
    }
}

let keyNavigationForPagingHandler;
const addKeyNavigationForPagingListener = () => {
    if (!keyNavigationForPagingHandler) {
        keyNavigationForPagingHandler = (event) => keyNavigationForPaging(event);
        window.addEventListener('keyup', keyNavigationForPagingHandler);
    }
}
const removeKeyNavigationForPagingListener = () => {
    if (keyNavigationForPagingHandler) {
        window.removeEventListener('keyup', keyNavigationForPagingHandler);
        keyNavigationForPagingHandler = null;
    }
}

function swipeNavigationForPaging(event) {
    if (document.activeElement.tagName === 'INPUT' || document.querySelector('.modal.show')) return;
    if (event.direction === Hammer.DIRECTION_LEFT) {
        changePage(sharedState.currentPage + 1);
    } else if (event.direction === Hammer.DIRECTION_RIGHT) {
        changePage(sharedState.currentPage - 1);
    }
}

let swipeNavigationForPagingHandler;
let hammer = null;
const addSwipeNavigationForPagingListener = () => {
    if (!swipeNavigationForPagingHandler) {
        hammer = new Hammer(document.querySelector('.file-list'));
        hammer.get('swipe').set({
            threshold: 50,
            velocity: 0.3,
            direction: Hammer.DIRECTION_HORIZONTAL,
        });

        swipeNavigationForPagingHandler = (event) => swipeNavigationForPaging(event);
        hammer.on('swipe', swipeNavigationForPagingHandler);
    }
}
const removeSwipeNavigationForPagingListener = () => {
    if (swipeNavigationForPagingHandler) {
        hammer.off('swipe', swipeNavigationForPagingHandler);
        swipeNavigationForPagingHandler = null;
        hammer = null;
    }
}
