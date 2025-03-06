import {eventBus} from "event-bus";
import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
<div ref="confirmModal" class="modal fade" id="confirmModal" tabindex="-1" style="z-index: 1060">
    <div class="modal-dialog modal-fullscreen-md-down modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="confirmModalLabel">{{ confirmData.title }}</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body text-center">
                <span>{{ confirmData.message }}</span>
                <div v-if="confirmData.file" class="small alert alert-warning text-break">{{ confirmData.file ? confirmData.file.split('/').pop() : '' }}</div>
                <div id="confirmModalExtras" class="mt-2"></div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="button" @click="confirmData.action(confirmData)" data-bs-dismiss="modal" class="btn btn-danger">{{ confirmData.submit || 'OK' }}</button>
            </div>
        </div>
    </div>
</div>
`

export const ConfirmDialog = {
    template: template,
    props: {
    },
    setup() {
        return { sharedState, settings };
    },
    data() {
        return {
            confirmData: {},
            modal: null,
        }
    },
    computed: {
    },
    methods: {
        showConfirmDialog(data = {}) {
            this.confirmData = data;

            const confirmElement = this.$refs.confirmModal;
            if (!this.modal) {
                this.modal = new bootstrap.Modal(confirmElement);
            }
            this.modal.show();
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
        this.removeToastListener = eventBus.on('show-confirm-dialog', (data) => {
            this.showConfirmDialog(data);
        });
    }

}

