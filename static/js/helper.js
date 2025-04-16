import {eventBus} from "event-bus";
import {sharedState} from "shared-state";

/**
 * Format file size from bytes to human-readable format
 *
 * @param bytes - File size in bytes
 * @returns {string} - Formatted file size
 */
export function formatFileSize(bytes) {
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 Byte';
    const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
    return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i];
}

/**
 * Format duration from seconds to human-readable format
 *
 * @param seconds - Duration in seconds
 * @returns {string} - Formatted duration
 */
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

/**
 * Format a date from epoch seconds to a human-readable format
 *
 * @param epochSeconds - Epoch seconds to format
 * @returns {string} - Formatted date
 */
export function formatDate(epochSeconds) {
    if (epochSeconds < 1) {
        return '';
    }
    const date = new Date(epochSeconds * 1000);
    const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' };
    return date.toLocaleDateString(undefined, options);
}

/**
 * Show a toast message
 *
 * @param message - Message to show
 * @param options - Options for the toast
 */
export function showToast(message, options = {}) {
    eventBus.emit('show-toast', { message, options });
}

/**
 * Show a confirm dialog
 *
 * @param data - object with Data to show in the dialog
 */
export function showConfirmDialog(data = {}) {
    eventBus.emit('show-confirm-dialog', data);
}

export function hideConfirmDialog() {
    eventBus.emit('hide-confirm-dialog');
}

export function showVideoPlayer(data = {}) {
    eventBus.emit('show-video-dialog', data);
}

export function hideVideoPlayer() {
    eventBus.emit('hide-video-dialog');
}

export function playVideo(file = {}) {
    eventBus.emit('play-video', file);
}


/**
 * Fetch files from the server
 *
 * @param data - object with Data to for fetching files
 */
export function fetchFiles(data = {}) {
    eventBus.emit('fetch-files', data);
}

/**
 * Debounce function to limit the number of calls to a function
 *
 * @param func - Function to call
 * @param wait - Time to wait before calling the function
 * @returns {(function(...[*]): void)|*}
 */
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
 * @param showToastMessage  - Show the API response in a toast (default: true)
 * @param onError - Function to call on error (default: null)
 * @param options - Fetch options (default: { method: 'GET' })
 * @returns {Promise<any>} - Promise with the API response
 */
export function apiCall(url,
                        { errorMessage = 'Error fetching data', showToastMessage = true,
                          onError = null,
                          options = { method: 'GET' } }) {
    return fetch(url, options)
        .then(response => response.json())
        .then(data => {
            if (showToastMessage) {
                showToast(data);
            }
            return data;
        })
        .catch(error => {
            console.error(errorMessage ? errorMessage : 'Error:', error);
            showToast(errorMessage);
            if (onError) {
                onError(error);
            }
        });
}

/**
 * set the video URL and emit the event to trigger postVideoUrl
 *
 * @param url - URL to set
 * @param stream - Stream the video (default: false)
 */
export function videoUrl(url, stream = false) {
    eventBus.emit('video-url', { url, stream });
}

export function handleViewChange(view) {
    sharedState.currentView = view;
    history.replaceState(null, '', view ? `/${view}` : '/');
}