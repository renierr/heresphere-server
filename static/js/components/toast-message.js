import {eventBus} from "event-bus";
import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
<div aria-live="polite" aria-atomic="true" class="position-fixed top-0 start-50 translate-middle-x p-3" style="z-index: 1100;">
    <div ref="toastElement" :style="{ width: wide ? 'auto' : '' }" class="toast text-bg-info border-0" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="toast-header">
            <strong class="me-auto">{{ title }}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            <span v-if="useHtml" v-html="message"></span>
            <span v-else>{{ message }}</span>
        </div>
    </div>
</div>
`

export const ToastMessage = {
    template: template,
    setup() {
        return { sharedState, settings };
    },
    data() {
        return {
            removeToastListener: null,
            title: 'Message',
            message: '',
            useHtml: false,
            wide: false,
        }
    },
    methods: {
        showToast(input, options = {}) {
            const { title = 'Message', stayOpen = false, asHtml = false, wide = false } = options;
            let message;
            try {
                if (input !== null && typeof input === 'object') {
                    message = input.message || JSON.stringify(input);
                } else {
                    message = input;
                }
            } catch (e) {
                message = input;
            }

            this.title = title;
            this.message = message;
            this.useHtml = asHtml;
            this.wide = wide;

            const toastElement = this.$refs.toastElement;
            const toast = new bootstrap.Toast(toastElement, { autohide: !options.stayOpen });
            toast.show();
        }
    },
    beforeUnmount() {
        if (this.removeToastListener) {
            this.removeToastListener();
            this.removeToastListener = null;
        }
        this.title = 'Message';
        this.message = '';
        this.useHtml = false;
    },
    mounted() {
        this.removeToastListener = eventBus.on('show-toast', ({ message, options }) => {
            this.showToast(message, options);
        });
    }

}
