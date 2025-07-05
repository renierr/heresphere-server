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
            <div ref="videoModalBody" class="modal-body position-relative" id="videoModalBody"></div>
            <div ref="videoModalFooter" class="modal-footer" id="videoModalFooter"></div>
        </div>
    </div>
</div>
`

export const VideoPlayer = {
    template: template,
    setup() {
        return { sharedState, settings };
    },
    data() {
        return {
            modal: null,
            listener: [],
        }
    },
    methods: {
        showPlayer(data = {}) {
            // TODO maybe better in mounted or setup?
            const videoElement = this.$refs.videoModal;
            if (!this.modal) {
                this.modal = new bootstrap.Modal(videoElement);
                videoElement.addEventListener('hidden.bs.modal', () => {
                    const player = videojs('videoPlayer');
                    if (player && typeof player.dispose === 'function') {
                        player.dispose();
                    }
                    const videoFooterElement = this.$refs.videoModalFooter;
                    if (videoFooterElement) {
                        videoFooterElement.innerHTML = '';
                    }
                    const videoBodyElement = this.$refs.videoModalBody;
                    if (videoBodyElement) {
                        videoBodyElement.innerHTML = '';
                    }
                });
            }
            this.modal.show();
        },
        playVideo(file) {
            const videoModalBody = document.getElementById('videoModalBody');
            const videoModalTitle = document.getElementById('videoModalLabel');
            const videoModalFooter = document.getElementById('videoModalFooter');

            videoModalFooter.innerHTML = '';
            videoModalTitle.textContent = file.title || 'Video Player';
            videoModalBody.innerHTML = `
            <video-js id="videoPlayer" class="vjs-default-skin w-100" controls autoplay referrerpolicy="no-referrer">
                <source src="${file.filename}" type="video/mp4">
            </video-js>
            `;
            videojs('videoPlayer');
            this.showPlayer();
        },
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
        this.listener.push(eventBus.on('play-video', (file) => {
            this.playVideo(file);
        }));

    }

}

