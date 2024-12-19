// Function to apply the theme
function applyTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
}

// Load the stored theme on page load
document.addEventListener('DOMContentLoaded', () => {
    const storedTheme = localStorage.getItem('theme');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const defaultTheme = storedTheme || (prefersDarkScheme ? 'dark' : 'light');
    applyTheme(defaultTheme);

    // Initialize the switch state based on the stored theme
    const themeToggle = document.getElementById('theme-toggle');
    themeToggle.checked = defaultTheme === 'dark';

    // Toggle theme and store the selection
    themeToggle.addEventListener('change', () => {
        const newTheme = themeToggle.checked ? 'dark' : 'light';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    });
});

