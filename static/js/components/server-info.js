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
}