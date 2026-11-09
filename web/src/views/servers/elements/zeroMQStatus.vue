<template>
    <span
        v-if="hasStatus"
        :class="textClass"
        :title="title"
    >
        <span :class="['fas', glyph]"></span>
        <span class="sr-only">{{ statusMessage }}</span>
    </span>
</template>

<script>
import { mapState } from "vuex"
import { healthCellMixin, isProblem, toneTextClass, toneTitle } from "@/helpers/healthCells"

const STATUS_MESSAGES = {
    0: "OK",
    1: "Not enabled",
    2: "Python library not installed correctly",
    3: "ZMQ script not running",
}

export default {
    name: "zeroMQStatus",
    mixins: [healthCellMixin],
    props: {
        server_id: {
            required: true,
            type: Number,
        },
    },
    computed: {
        ...mapState({
            zeromq: state => state.servers.zeromq,
        }),
        status() {
            return this.zeromq[this.server_id]
        },
        hasStatus() {
            return this.status !== undefined
        },
        statusOk() {
            return this.hasStatus && this.status == 0
        },
        statusMessage() {
            return STATUS_MESSAGES[this.status] || "Unknown status code"
        },
        tone() {
            return this.healthTone(this.server_id, "zmq")
        },
        // ZeroMQ switched off is not an issue: drawn as "off", not as an error
        glyph() {
            if (this.statusOk) {
                return "fa-check"
            }
            return this.tone !== null && !isProblem(this.tone) ? "fa-minus" : "fa-times"
        },
        textClass() {
            if (this.tone === null) {
                return this.statusOk ? "text-success" : "text-danger"
            }
            return toneTextClass(this.tone, this.statusOk ? "text-success" : "text-muted")
        },
        title() {
            const why = toneTitle(this.tone)
            return why ? `${this.statusMessage}\n${why}` : this.statusMessage
        },
    },
}
</script>
