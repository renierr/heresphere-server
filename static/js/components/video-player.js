class VideoPlayerElement extends HTMLElement {

    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = `
<div class="modal fade" id="videoModal" tabindex="-1">
  <div class="modal-dialog modal-fullscreen modal-dialog-scrollable">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="videoModalLabel">Video Player</h5>
        <button type="button" class="btn-close" aria-label="Close"></button>
      </div>
      <div class="modal-body position-relative" id="videoModalBody"></div>
      <div class="modal-footer" id="videoModalFooter"></div>
    </div>
  </div>
</div>
        `;
    }

    connectedCallback() {
        const videoModalBody = this.shadowRoot.getElementById('videoModalBody');
        const videoModalTitle = this.shadowRoot.getElementById('videoModalLabel');
        const videoModalFooter = this.shadowRoot.getElementById('videoModalFooter');

        videoModalFooter.innerHTML = '';
        videoModalTitle.textContent = this.getAttribute('title') || 'Video Player';
        videoModalBody.innerHTML = `
            <video-js id="videoPlayer" class="vjs-default-skin w-100" controls autoplay>
                <source src="${this.getAttribute('src')}" type="video/mp4">
            </video-js>
        `;
        const player = this.shadowRoot.getElementById('videoPlayer');
        videojs(player);
        const videoModalEl = this.shadowRoot.getElementById('videoModal');
        const videoModal = new bootstrap.Modal(videoModalEl);
        videoModal.show();

        this.shadowRoot.querySelector('.btn-close').addEventListener('click', () => {
            videoModal.hide();
            videojs(player).dispose();
            videoModalEl.remove();
            this.remove();
        });

    }
}

customElements.define('video-player', VideoPlayerElement);
