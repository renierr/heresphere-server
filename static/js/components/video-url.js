import { sharedState, settings } from "shared-state";
import { showToast } from "helper";

// language=Vue
const template = `
<div class="w-100 d-flex gap-2 align-items-center flex-row p-2">
    <div class="form-floating flex-grow-1">
        <input id="videoInput" type="text" v-model="videoUrl" placeholder="video URL" class="form-control" @keyup.enter="postVideoUrl(false)">
        <label class="text-muted" for="videoInput">Video URL...</label>
        <button v-if="videoUrl" class="btn btn-outline-secondary bg-transparent border-0 position-absolute end-0 top-0 h-100" type="button" @click="videoUrl = ''"><i class="bi bi-x"></i></button>
    </div>
    <div class="">
        <button @click="postVideoUrl(false)" class="btn btn-sm btn-outline-primary">Download</button>
        <button @click="postVideoUrl(true)" class="btn btn-sm btn-outline-success">Stream</button>
    </div>
</div>
`

export const VideoUrl = {
    template: template,
    props: {
    },
    setup() {
        return { sharedState, settings };
    },
    data() {
        return {
            videoUrl: '',
            removeVideoUrlListener: null,
        }
    },
    computed: {
    },
    methods: {
        postVideoUrl(stream=false) {
            if (this.videoUrl.trim() === '') {
                showToast('Please enter a URL');
                return;
            }
            fetch(stream ? '/stream' : '/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ sourceUrl: this.videoUrl, url: this.videoUrl })
            })
                .then(response => response.json())
                .then(data => {
                    if (stream) {
                        const video_url = data.videoUrl;
                        const audio_url = data.audioUrl;
                        const videoModalTitle = document.getElementById('videoModalLabel');
                        const modalBody = document.getElementById('videoModalBody');
                        const modalFooter = document.getElementById('videoModalFooter');
                        if (modalBody && modalFooter && video_url) {
                            // strip trailing / from video url
                            const video_source = video_url.replace(/\/+$/, '');
                            const title = data.title || 'Video Streaming...';
                            videoModalTitle.textContent = title;
                            modalBody.innerHTML = `
                                <video-js id="videoPlayer" class="vjs-default-skin w-100 h-100" controls autoplay>
                                    <source src="${video_source}" type="video/webm">
                                </video-js>
                            `;
                            videojs('videoPlayer');
                            modalFooter.innerHTML = `
                                <a href="${this.videoUrl}" target="_blank">Video URL provided</a>
                                <a href="${video_source}" target="_blank">Extracted Video link</a>
                            `;

                            const tempVideoUrl = this.videoUrl;
                            const downloadButton = document.createElement('button');
                            downloadButton.textContent = 'Trigger Download';
                            downloadButton.classList.add('btn', 'btn-primary', 'btn-sm');
                            downloadButton.addEventListener('click', () => {
                                window.videoModal.hide();
                                this.redownload({ url: tempVideoUrl });
                            });
                            modalFooter.appendChild(downloadButton);

                            if (navigator.share) {
                                const shareButton = document.createElement('button');
                                shareButton.textContent = 'Share Video';
                                shareButton.classList.add('btn', 'btn-secondary', 'btn-sm');
                                shareButton.addEventListener('click', () => {
                                    navigator.share({
                                        title: title,
                                        url: tempVideoUrl,
                                    })
                                        .then(() => console.log(`Successful shared ${tempVideoUrl}`))
                                        .catch((error) => console.log('Error sharing', error));
                                });
                                modalFooter.appendChild(shareButton);
                                const shareExtractedButton = document.createElement('button');
                                shareExtractedButton.textContent = 'Share Extracted Video';
                                shareExtractedButton.classList.add('btn', 'btn-secondary', 'btn-sm');
                                shareExtractedButton.addEventListener('click', () => {
                                    navigator.share({
                                        title: title,
                                        url: video_source,
                                    })
                                        .then(() => console.log(`Successful shared ${tempVideoUrl}`))
                                        .catch((error) => console.log('Error sharing', error));
                                });
                                modalFooter.appendChild(shareExtractedButton);
                            }
                            window.videoModal.show();
                            this.videoUrl = '';
                        } else {
                            showToast('Error: No video URL found to be played');
                        }
                    } else {
                        showToast(data);
                    }
                })
                .catch(error => {
                    showToast('Error download/stream file: ' + error);
                    console.error('Error:', error);
                });
        },
    },
    beforeUnmount() {
        if (this.removeVideoUrlListener) {
            this.removeVideoUrlListener();
            this.removeVideoUrlListener = null;
        }
    },
    mounted() {
        this.removeVideoUrlListener = eventBus.on('video-url', ({url, stream = false }) => {
            console.log('Received video URL:', url);
            this.videoUrl = url;
            this.postVideoUrl(stream);
        });
    }
}