<template>
    <span
        v-if="proxy !== '' && proxy !== undefined"
        :class="['text-nowrap', textClass]"
        :title="title"
    >
        <span :class="['fas', working ? 'fa-check' : 'fa-times']"></span>
        {{ working ? '' : proxy }}
    </span>
</template>

<script>
import { healthCellMixin, isProblem, toneTextClass, toneTitle } from "@/helpers/healthCells"

const NOT_CONFIGURED = "not configured (so not tested)"

export default {
    name: "proxyStatus",
    mixins: [healthCellMixin],
    props: {
        proxy: {},
        server_id: {
            type: Number,
            default: null,
        },
    },
    computed: {
        tone() {
            return this.healthTone(this.server_id, "proxy")
        },
        // Without health: only an unconfigured proxy is fine, as before
        working() {
            return this.tone === null ? this.proxy == NOT_CONFIGURED : !isProblem(this.tone)
        },
        textClass() {
            return this.tone === null ? (this.working ? "text-success" : "text-danger") : toneTextClass(this.tone)
        },
        title() {
            const status = this.proxy == NOT_CONFIGURED ? "Not configured" : this.proxy
            const why = toneTitle(this.tone)
            return why ? `${status}\n${why}` : status
        },
    },
}
</script>
