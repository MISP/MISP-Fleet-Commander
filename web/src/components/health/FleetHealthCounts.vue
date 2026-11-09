<template>
    <!-- A button, not a link: the fleet list items are links themselves -->
    <button
        v-if="loaded && server_count > 0"
        type="button"
        :class="['fleet-health', { healthy: total === 0 }]"
        :title="title"
        :aria-label="`${title}. Show in Needs attention`"
        @click.stop.prevent="openAttention"
    >
        <template v-if="total > 0">
            <span
                v-for="severity in shownSeverities"
                :key="severity"
                :class="['fleet-health-chip', `sev-${severity}`]"
            >
                <i :class="[severityMeta[severity].icon, 'fleet-health-icon']" aria-hidden="true"></i>{{ counts[severity] }}
            </span>
        </template>
        <span v-else class="fleet-health-ok">
            <i class="fas fa-check mr-1" aria-hidden="true"></i>Healthy
        </span>
    </button>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import { SEVERITIES, emptyCounts } from "@/store/modules/health"
import { SEVERITY_META, countsText } from "@/views/attention/healthLabels"

export default {
    name: "FleetHealthCounts",
    props: {
        fleet_id: { type: Number, required: true },
        server_count: { type: Number, default: 0 },
    },
    data() {
        return {
            severityMeta: SEVERITY_META,
        }
    },
    computed: {
        ...mapState({
            loaded: state => state.health.loaded,
        }),
        ...mapGetters({
            fleetCounts: "health/fleetCounts",
        }),
        counts() {
            return this.fleetCounts[this.fleet_id] || emptyCounts()
        },
        total() {
            return this.counts.critical + this.counts.warning + this.counts.info
        },
        shownSeverities() {
            return SEVERITIES.filter(severity => this.counts[severity] > 0)
        },
        title() {
            return this.total > 0 ? countsText(this.counts) : "No issues"
        },
    },
    methods: {
        openAttention() {
            this.$router.push({ name: "attention", query: { fleet_id: String(this.fleet_id) } }).catch(() => {})
        },
    },
}
</script>

<style scoped>
.fleet-health {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.1rem 0.2rem;
    margin: 0;
    border: 1px solid transparent;
    border-radius: 0.8rem;
    background: transparent;
    font: inherit;
    font-size: 0.75rem;
    font-weight: 600;
    line-height: 1;
    font-variant-numeric: tabular-nums;
    cursor: pointer;
}

.fleet-health:hover {
    border-color: var(--health-rule);
    background: rgba(255, 255, 255, 0.6);
}

.fleet-health:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 1px;
}

.fleet-health-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    height: 1.3rem;
    padding: 0 0.45rem;
    border: 1px solid transparent;
    border-radius: 0.65rem;
}

.fleet-health-chip.sev-critical {
    color: var(--health-critical-ink);
    background: var(--health-critical-tint);
    border-color: var(--health-critical);
}

.fleet-health-chip.sev-warning {
    color: var(--health-warning-ink);
    background: var(--health-warning-tint);
    border-color: var(--health-warning);
}

.fleet-health-chip.sev-info {
    color: var(--health-info-ink);
    background: var(--health-info-tint);
    border-color: var(--health-info);
}

.fleet-health-ok {
    display: inline-flex;
    align-items: center;
    height: 1.3rem;
    padding: 0 0.3rem;
    color: var(--health-ok-ink);
    font-weight: 500;
}
</style>
