import {eventBus} from "../event-bus.js";

export const ServerInfo = {
    template: '#server-info-template',
    props: {
        settings: {},
    },
    data() {
        return {
            serverOutput: '',
            serverResult: '',
        };
    },
    methods: {
        openAndHandleSSEConnection(call_func) {
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
                if (call_func)  {
                    call_func(event);
                }
            };
            return eventSource;
        },
    },
    mounted() {
        this.openAndHandleSSEConnection();
    }
}