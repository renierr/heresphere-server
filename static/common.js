import {showToast, fetchFiles,  showConfirmDialog, hideConfirmDialog} from "helper";

export const methods = {



    showMessage: function (input, options = {}) {
        showToast(input, options);
    },
    confirmDeleteFile(filename) {
        this.confirmData = {
            title: 'Delete file',
            message: `Are you sure you want to delete the following file?`,
            file: filename,
            submit: 'Delete',
            action: this.deleteFile,
        }
        window.confirmModal.show();
    },
    deleteFile(confData) {
        if (!confData && !confData.file) {
            this.showMessage('Wrong number of parameters for deleteFile');
            return;
        }
        const file = confData.file;
        const utf8Bytes = new TextEncoder().encode(file);
        const encodedUrl = btoa(String.fromCharCode(...utf8Bytes));
        this.confirmData = {};
        fetch(`/api/files?url=${encodeURIComponent(encodedUrl)}`, {
            method: 'DELETE',
        })
            .then(response => response.json())
            .then((data) => {
                this.serverResult = data;
                fetchFiles(true);
            })
            .catch(error => {
                console.error('Error deleting bookmark:', error);
            });
    },


    confirmRenameFile(file) {
        const modalConfirmExtras = document.getElementById('confirmModalExtras'); // TODO implement extras handling
        const currentName = file.title || file.filename.split('/').pop().split('.').slice(0, -1).join('.');;
        modalConfirmExtras.innerHTML = `
            <div class="d-flex align-items-center flex-column flex-md-row">
                <input id="confModal_fileName" class="form-control" type="text" />
            </div>
            `;
        const nameInput = document.getElementById('confModal_fileName');
        nameInput.value = currentName;
        this.confirmData = {
            title: 'Rename file',
            message: `Rename the title for the following file:`,
            file: file.filename,
            submit: 'Rename',
            action: (confData) => {
                let newName = nameInput.value;
                if (newName === currentName) {
                    this.showMessage('New name is the same as the current name');
                    return;
                }
                this.renameFile(confData, newName);
            },
        }
        showConfirmDialog(this.confirmData);
        //window.confirmModal.show();
        nameInput.addEventListener('keydown', (evt) => {
            if (evt.key === 'Enter') {
                evt.preventDefault();
                hideConfirmDialog();
                this.confirmData.action(this.confirmData)
            }
        });

    },
    renameFile(confData, newName) {
        if (!confData && !confData.file) {
            this.showMessage('Wrong number of parameters for move to library');
            return;
        }
        const file = confData.file;
        this.confirmData = {};
        fetch('/api/rename', {
            method: 'POST',
            body: JSON.stringify({ video_path: file, newName: newName }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(data => {
                this.serverResult = data;
                fetchFiles(true);
            })
            .catch(error => {
                console.error('Error renaming file:', error);
                this.serverResult = 'Error renaming file: ' + error;
            });
    },

    confirmMoveFile(file) {
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
                    <option value="">Move to library root folder</option>
                    <option value="~videos~">Move to videos folder</option>
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
                this.moveFile(confData, subfolderSelection);
            },
        }
        window.confirmModal.show();
    },
    moveFile(confData, subfolder) {
        if (!confData && !confData.file) {
            this.showMessage('Wrong number of parameters for move to library');
            return;
        }
        const file = confData.file;
        this.settings.lastMoveSubfolder = subfolder;
        this.saveSettings();
        this.confirmData = {};
        fetch('/api/move_file', {
            method: 'POST',
            body: JSON.stringify({ video_path: file, subfolder: subfolder }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
          .then(response => response.json())
          .then(data => {
              this.serverResult = data;
              fetchFiles(true);
          })
          .catch(error => {
              console.error('Error moving file:', error);
              this.serverResult = 'Error moving file: ' + error;
          });

    },


};



