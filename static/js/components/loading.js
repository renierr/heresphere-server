import {eventBus} from "event-bus";
import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
<div id="loadingBar" class="loading-bar"></div>
<div class="card-body text-center">
    Loading...
    <div class="d-flex justify-content-center align-items-center" style="min-height: 140px;">
        <div class="spinner-border text-secondary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    </div>
</div>
`

export const Loading = {
    template: template,
    props: {
    },
    setup() {
        return { sharedState, settings };
    },
    data() {
    },
    computed: {
    },
    methods: {
    },
    mounted() {
    }
}