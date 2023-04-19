<template>
    <span
        :class="statusOk ? 'text-success' : 'text-danger'"
        :title="statusMessage"
    >
        <span :class="['fas', statusOk ? 'fa-check' : 'fa-times']"></span>
    </span>
</template>

<script>
import { mapState, mapGetters } from "vuex"

export default {
    name: "zeroMQStatus",
    props: {
        server_id: {
            required: true,
            type: Number,
        },
    },
    data: function () {
        return {
            statusMapping: {
                0: 'OK',
                1: 'Not enabled',
                2: 'Python library not installed correctly',
                3: 'ZMQ script not running',
            }
        }
    },
    computed: {
        ...mapState({
            zeromq: state => state.servers.zeromq,
        }),
        status() {
            return this.zeromq[this.server_id]
        },
        statusOk () {
            return this.status !== undefined && this.status == 0
        },
        statusMessage () {
            return this.statusMapping[this.status] || 'Unknown status code'
        },
    },
    methods: {
    }
}
</script>

<style scoped>

</style>