import {eventBus} from "event-bus";
import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
<button ref="scroll-to-top" id="scroll-to-top"
        @click="scrollTop"
        class="fs-2 btn btn-info position-fixed bottom-0 end-0 m-3 rounded-circle d-none shadow d-flex align-items-center justify-content-center" 
        title="Scroll to top">
    <i class="bi bi-arrow-up-short"></i>
</button>
`

let scrollListenerHandler = null;
export const ScrollTop = {
    template: template,
    props: {
    },
    setup() {
        return { sharedState, settings };
    },
    computed: {
    },
    methods: {
        scrollTop() {
            window.scrollTo({top: 0, behavior: 'smooth'});
        }
    },
    beforeUnmount() {
        if (scrollListenerHandler)  {
            window.removeEventListener('scroll', scrollListenerHandler);
            scrollListenerHandler = null;
        }
    },
    mounted() {
        const scrollButton = this.$refs['scroll-to-top'];
        scrollListenerHandler = () => {
            if (window.scrollY > 100) {
                scrollButton.classList.remove('d-none');
            } else {
                scrollButton.classList.add('d-none');
            }
        }
        window.addEventListener('scroll', scrollListenerHandler);
    }
}