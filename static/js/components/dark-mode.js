import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
<div class="form-check form-switch">
    <input class="form-check-input" type="checkbox" id="theme-toggle" v-model="isDarkMode">
    <label class="form-check-label" for="theme-toggle">Dark Mode</label>
</div>
`

export const DarkMode = {
    template: template,
    data() {
        return {
            isDarkMode: false,
        }
    },
    setup() {
        return { sharedState, settings };
    },
    methods: {
        applyTheme(isDark) {
            const theme = isDark ? 'dark' : 'light';
            document.documentElement.setAttribute('data-bs-theme', theme);
            localStorage.setItem('theme', theme);
        }
    },
    watch: {
        isDarkMode: function (newTheme) {
            this.applyTheme(newTheme);
        }
    },
    mounted() {
        const storedTheme = localStorage.getItem('theme');
        const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)').matches;
        this.isDarkMode = storedTheme ? storedTheme === 'dark' : prefersDarkScheme;
        this.applyTheme(this.isDarkMode);
    }
}