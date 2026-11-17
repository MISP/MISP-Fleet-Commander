<template>
    <span
        v-if="issues.length > 0"
        :class="['issues-chip', `sev-${worst}`]"
        :title="summary"
        role="img"
        :aria-label="summary"
    >
        <i :class="severityMeta[worst].icon" aria-hidden="true"></i>
        <span>{{ issues.length }}</span>
    </span>
</template>

<script>
import { mapState } from "vuex"
import { SEVERITY_META, countsText } from "@/views/attention/healthLabels"
import { EMPTY_DIGEST } from "@/store/modules/health"

// The server's unacknowledged issues, for the zoomed-out node views: sized relative to the text around it
export default {
    name: "NodeIssuesChip",
    props: {
        server_id: { type: Number, required: true },
    },
    data() {
        return {
            severityMeta: SEVERITY_META,
        }
    },
    computed: {
        ...mapState({
            digest(state) {
                return state.health.digests[this.server_id] || EMPTY_DIGEST
            },
        }),
        issues() {
            return this.digest.active
        },
        worst() {
            return this.digest.worst
        },
        summary() {
            return `Server: ${countsText(this.digest.counts)}`
        },
    },
}
</script>

<style scoped>
.issues-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    height: 1.55em;
    padding: 0 0.5em;
    border: 2px solid transparent;
    border-radius: 0.8em;
    font-size: 0.7em;
    font-weight: 600;
    line-height: 1;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    cursor: default;
}

.issues-chip i {
    font-size: 0.85em;
}

.sev-critical {
    color: var(--health-critical-ink);
    background: var(--health-critical-tint);
    border-color: var(--health-critical);
}

.sev-warning {
    color: var(--health-warning-ink);
    background: var(--health-warning-tint);
    border-color: var(--health-warning);
}

.sev-info {
    color: var(--health-info-ink);
    background: var(--health-info-tint);
    border-color: var(--health-info);
}
</style>
