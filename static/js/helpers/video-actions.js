import { apiCall, showToast, fetchFiles, showConfirmDialog, hideConfirmDialog } from "helper";
import { settings } from "shared-state";

export function confirmDeleteFile(filename) {
    const confirmData = {
        title: 'Delete file',
        message: `Are you sure you want to delete the following file?`,
        file: filename,
        submit: 'Delete',
        action: deleteFile,
    }
    showConfirmDialog(confirmData);
}

function deleteFile(confData) {
    if (!confData && !confData.file) {
        showToast('Wrong number of parameters for deleteFile');
        return;
    }
    const file = confData.file;
    const utf8Bytes = new TextEncoder().encode(file);
    const encodedUrl = btoa(String.fromCharCode(...utf8Bytes));
    apiCall(`/api/files?url=${encodeURIComponent(encodedUrl)}`, { errorMessage: 'Error deleting file',
        options: { method: 'DELETE'} })
        .then(data => {
            fetchFiles(true);
        });
}

export function confirmRenameFile(file) {
    const modalConfirmExtras = document.getElementById('confirmModalExtras');
    const currentName = file.title || file.filename.split('/').pop().split('.').slice(0, -1).join('.');
    modalConfirmExtras.innerHTML = `
    <div class="d-flex align-items-center flex-column flex-md-row">
        <input id="confModal_fileName" class="form-control" type="text" />
    </div>
    `;
    const nameInput = document.getElementById('confModal_fileName');
    nameInput.value = currentName;
    const confirmData = {
        title: 'Rename file',
        message: `Rename the title for the following file:`,
        file: file.filename,
        submit: 'Rename',
        action: (confData) => {
            let newName = nameInput.value;
            if (newName === currentName) {
                showToast('New name is the same as the current name');
                return;
            }
            renameFile(confData, newName);
        },
    }
    showConfirmDialog(confirmData);
    nameInput.addEventListener('keydown', (evt) => {
        if (evt.key === 'Enter') {
            evt.preventDefault();
            hideConfirmDialog();
            confirmData.action(confirmData)
        }
    });
}

function renameFile(confData, newName) {
    if (!confData && !confData.file) {
        showToast('Wrong number of parameters for move to library');
        return;
    }
    const file = confData.file;
    const postOptions = {
        method: 'POST',
        body: JSON.stringify({ video_path: file, newName: newName }),
        headers: { 'Content-Type': 'application/json' }
    };
    apiCall('/api/rename', { errorMessage: 'Error renaming file',
        options: postOptions })
        .then(data => {
            fetchFiles(true);
        });
}

export function confirmMoveFile(file) {
    const lastFolder = settings.lastMoveSubfolder || '';
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
    const confirmData = {
        title: 'Move file',
        message: `Are you sure you want to move the following file inside library?`,
        file: file.filename,
        submit: 'Move',
        action: (confData) => {
            let subfolderSelection = document.getElementById('subfolderSelect').value;
            if (file.folder === subfolderSelection) {
                showToast('Cannot move file inside its own folder');
                return;
            }
            moveFile(confData, subfolderSelection);
        },
    }
    showConfirmDialog(confirmData);
}

function moveFile(confData, subfolder) {
    if (!confData && !confData.file) {
        showToast('Wrong number of parameters for move to library');
        return;
    }
    const file = confData.file;
    settings.lastMoveSubfolder = subfolder;
    const postOptions = {
        method: 'POST',
        body: JSON.stringify({ video_path: file, subfolder: subfolder }),
        headers: { 'Content-Type': 'application/json' }
    };
    apiCall('/api/move_file', { errorMessage: 'Error moving file',
        options: postOptions })
        .then(data => {
            fetchFiles(true);
        });
}

export function generateThumbnail(file) {
    apiCall('/api/generate_thumbnail', { errorMessage: 'Error generating thumbnail',
        showToastMessage: false,
        options: { method: 'POST', body: JSON.stringify({ video_path: file }), headers: {'Content-Type': 'application/json'} } })
        .then(data => showToast(data.success ? data : 'Failed to generate thumbnail'));
}

export function showDuplicateInfo(file) {
    if (file.may_exist) {
        let message = file.may_exist.split('\n');
        message = message.map((line) => {
            if (line.includes('id[')) {
                return `<h5>${line}</h5>`
            } else {
                return `<p>${line}</p>`;
            }
        }).join('<br>');
        showToast(message, {title: "Duplicates", stayOpen: true, asHtml: true, wide: true});
    }
}