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
        confirmMoveInsideLibrary(file) {
            const lastFolder = this.settings.lastMoveSubfolder || '';
            const modalConfirmExtras = document.getElementById('confirmModalExtras');
            const options = library_subfolders.map(subfolder => {
                const selected = subfolder === lastFolder ? 'selected' : '';
                return `<option value="${subfolder}" ${selected}>${subfolder}</option>`;
            }).join('');
            modalConfirmExtras.innerHTML = `
            <div class="d-flex align-items-center flex-column flex-md-row">
                <label for="subfolderSelect" class="form-label me-2 text-nowrap">Target Subfolder</label>
                <select id="subfolderSelect" class="form-select">
                    <option value="">Select a subfolder or leave for root folder</option>
                    ${options}
                </select>
            </div>
            `;
            this.confirmData = {
                title: 'Move file',
                message: `Are you sure you want to move the following file inside library?`,
                file: file.filename,
                submit: 'Move',
                action: (confData) => {
                    let subfolderSelection = document.getElementById('subfolderSelect').value;
                    if (file.folder === subfolderSelection) {
                        this.showMessage('Cannot move file inside its own folder');
                        return;
                    }
                    this.moveInsideLibrary(confData, subfolderSelection);
                },
            }
            const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
            modal.show();
            // clear extras on modal close
            modal._element.addEventListener('hidden.bs.modal', () => {
                modalConfirmExtras.innerHTML = '';
            });
        },
        moveInsideLibrary(confData, subfolder) {
            if (!confData && !confData.file) {
                this.showMessage('Wrong number of parameters for move to library');
                return;
            }
            const file = confData.file;
            this.settings.lastMoveSubfolder = subfolder;
            this.saveSettings();
            this.confirmData = {};
            fetch('/api/move_inside_library', {
                method: 'POST',
                body: JSON.stringify({ video_path: file, subfolder: subfolder }),
                headers: {
                    'Content-Type': 'application/json'
                }
            })
                .then(response => response.json())
                .then(data => {
                    this.serverResult = data;
                    this.fetchFiles(true);
                })
                .catch(error => {
                    console.error('Error moving file:', error);
                    this.serverResult = 'Error moving file: ' + error;
                });

        },

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
        const eventSource = new EventSource('/sse');
        const serverOutput = [];
        eventSource.onmessage = event => {
            serverOutput.push(new Date().toLocaleTimeString() + ': ' + event.data);
            if (serverOutput.length > 100) {
                serverOutput.shift();
            }
            this.serverOutput = serverOutput.slice().reverse().join('\n');
            if (event.data.includes('Generate thumbnails finished')) {
                this.fetchFiles();
            }
        };
    }
});
