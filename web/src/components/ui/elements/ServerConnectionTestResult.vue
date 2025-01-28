<template>
    <span
        :class="{'text-nowrap': true, 'text-danger': getServerStatus.error, 'text-success': !getServerStatus.error}"
    >
        <b-icon v-if="getServerStatus.data !== undefined" icon="circle-fill"></b-icon>
        <template v-if="getServerStatus.error"> 
            {{ formatErrorMessage(getServerStatus.data) }}
            <b-alert v-if="full_message" variant="danger" class="text-wrap mt-2 mb-0" show>
                <div class="text-muted mb-1 text-right">Connection Test Took: {{ parseInt(getServerStatus.latency*1000) }}ms</div>
                {{ getServerStatus.data }}
            </b-alert>
        </template>
        <template v-else> {{ getServerStatus.data }}</template>
        <small
                v-if="getServerStatus.latency !== undefined && !full_message"
                :class="{'text-success': getServerStatus.latency < 0.3, 'text-warning': getServerStatus.latency >= 0.3 && getServerStatus.latency < 2, 'text-danger': getServerStatus.latency >= 2}"
        >
            {{ parseInt(getServerStatus.latency*1000) }}ms
        </small>
    </span>
</template>

<script>
import { mapState } from "vuex"

export default {
    name: "ServerConnectionTestResult",
    props: {
        server_id: {
            required: true,
            type: Number,
        },
        full_message: {
            required: false,
            type: Boolean,
            default: false,
        },
    },
    data: function() {
        return {}
    },
    computed: {
        ...mapState({
            server_status: state => state.servers.server_status,
        }),
        getServerStatus() {
            return this.server_status[this.server_id] || null
        }
    },
    methods: {
        formatErrorMessage(message) {
            if (message === undefined) {
                return ''
            }
            if (message.startsWith('Authentication failed')) {
                return 'Authentication failed'
            }
            if (message.includes('Connection Error:')) {
                return message.match(/\[([^\]]+)\]/)?.[1] || message
            }
            return message
        },
    },
}
</script>