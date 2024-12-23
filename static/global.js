// Function to apply the theme
function applyTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
}

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

    // scroll back to top button
    const scrollButton = document.getElementById('scroll-to-top');
    scrollButton.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    window.addEventListener('scroll', () => {
        if (window.scrollY > 100) {
            scrollButton.classList.remove('d-none');
        } else {
            scrollButton.classList.add('d-none');
        }
    });
});

