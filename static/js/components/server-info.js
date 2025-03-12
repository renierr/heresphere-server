import {eventBus} from "event-bus";
import {settings, sharedState} from "shared-state";

// language=Vue
const template = `
<div class="accordion" id="serverinfo">
    <div class="accordion-item">
        <h5 class="accordion-header">
            <button class="accordion-button btn-sm p-1" type="button"
                    data-bs-toggle="collapse" data-bs-target="#serverinfo-collapse"
                    aria-expanded="true" aria-controls="serverinfo-collapse"
                    @click="toggleInfoAccordion" :class="{collapsed: !settings.infoAccordionOpen}">
                Server Information
            </button>
        </h5>
    </div>
    <div class="accordion-item">
        <div id="serverinfo-collapse" class="accordion-collapse collapse" :class="{ show: settings.infoAccordionOpen }">
            <div class="accordion-body p-1">
                <div v-text="serverOutput" class="text-muted small" style="white-space: pre-wrap; overflow-y: auto; height: 100px;"></div>
            </div>
        </div>
    </div>
</div>
`

export const ServerInfo = {
    template: template,
    setup() {
        return { sharedState, settings };
    },
    data() {
        return {
            serverOutput: '',
        };
    },
    methods: {
        toggleInfoAccordion() {
            this.settings.infoAccordionOpen = !this.settings.infoAccordionOpen;
        },
        openAndHandleSSEConnection() {
            const eventSource = new EventSource('/sse');
            window.addEventListener('beforeunload', () => {
                eventSource.close();
                console.log('EventSource connection closed');
            });

            const serverOutput = [];
            eventSource.onmessage = event => {
                // ignore Heartbeat message
                if (event.data.includes('Heartbeat '))  return;

                serverOutput.push(new Date().toLocaleTimeString() + ': ' + event.data);
                if (serverOutput.length > 100) {
                    serverOutput.shift();
                }
                this.serverOutput = serverOutput.slice().reverse().join('\n');
                eventBus.emit('sse-message', event.data);
            };
            return eventSource;
        },
    },
    mounted() {
        this.openAndHandleSSEConnection();
    }
}