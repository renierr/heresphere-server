import {eventBus} from "event-bus";
import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
<div ref="videoModal" class="modal fade" id="videoModal" tabindex="-1">
    <div class="modal-dialog modal-fullscreen modal-dialog-scrollable">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="videoModalLabel">Video Player</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body position-relative" id="videoModalBody"></div>
            <div class="modal-footer" id="videoModalFooter"></div>
        </div>
    </div>
</div>
`

export const VideoPlayer = {
    template: template,
    props: {
    },
    setup() {
        return { sharedState, settings };
    },
    data() {
        return {
            modal: null,
            listener: [],
        }
    },
    computed: {
    },
    methods: {
        showPlayer(data = {}) {
            // TODO maybe better in mounted or setup?
            const videoElement = this.$refs.videoModal;
            if (!this.modal) {
                this.modal = new bootstrap.Modal(videoElement);
                videoElement.addEventListener('hidden.bs.modal', () => {
                });
            }
            this.modal.show();
        }
    },
    beforeUnmount() {
        this.listener.forEach(l => l());
        this.modal = null;
    },
    mounted() {
        this.listener.push(eventBus.on('show-video-dialog', (data) => {
            this.showPlayer(data);
        }));
        this.listener.push(eventBus.on('hide-video-dialog', () => {
            this.modal.hide();
        }));
    }

}

