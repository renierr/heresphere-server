import {eventBus} from "event-bus";

export function formatFileSize(bytes) {
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 Byte';
    const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
    return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i];
}

export function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

export function formatDate(epochSeconds) {
    if (epochSeconds < 1) {
        return '';
    }
    const date = new Date(epochSeconds * 1000);
    const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' };
    return date.toLocaleDateString(undefined, options);
}

export function showToast(message, options = {}) {
    eventBus.emit('show-toast', { message, options });
}

export function showConfirmDialog(data = {}) {
    eventBus.emit('show-confirm-dialog', data);
}

export function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        const later = () => {
            timeout = null;
        };
        const callNow = !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
}

/**
 * Make an API call to the given URL
 *
 * @param url - URL to call
 * @param errorMessage - Error message to show on failure (default: 'Error fetching data')
 * @param onSuccessCallback - Callback function to call on success (default: null)
 * @param options - Fetch options (default: { method: 'GET' })
 */
export function apiCall(url,
                        { errorMessage = 'Error fetching data',
                          onSuccessCallback,
                          options = { method: 'GET' } }) {
    fetch(url, options)
        .then(response => response.json())
        .then(data => {
            showToast(data);
            if (typeof onSuccessCallback === 'function') {
                onSuccessCallback(data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast(errorMessage);
        });
}