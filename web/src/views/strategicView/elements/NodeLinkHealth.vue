<template>
    <span
        v-if="counts !== null && counts.total > 0"
        :class="['link-health-chip', `link-health-${level}`, { 'link-health-large': large }]"
        :title="summary"
        role="img"
        :aria-label="summary"
    >
        <i :class="['fas', icon]" aria-hidden="true"></i>
        <span class="link-health-count">{{ shownCount }}</span>
    </span>
</template>

<script>
import { mapGetters } from "vuex"

const LABELS = {
    broken: "broken",
    degraded: "degraded",
    unknown: "not tested",
    ok: "OK",
    unused: "unused",
}

export default {
    name: "NodeLinkHealth",
    props: {
        server_id: { type: Number, required: true },
        // For the zoomed-out node views
        large: { type: Boolean, default: false },
    },
    computed: {
        ...mapGetters({
            linkHealthBySource: "connections/linkHealthBySource",
        }),
        counts() {
            return this.linkHealthBySource[this.server_id] || null
        },
        level() {
            // Only unused links: shown as neutral
            return this.counts.worst || "unused"
        },
        problemCount() {
            return this.counts.broken + this.counts.degraded + this.counts.unknown
        },
        shownCount() {
            return this.problemCount > 0 ? this.problemCount : this.counts.total - this.counts.unused
        },
        icon() {
            return { broken: "fa-unlink", degraded: "fa-link", unknown: "fa-link", ok: "fa-link", unused: "fa-link" }[this.level]
        },
        summary() {
            const parts = ["broken", "degraded", "unknown", "ok", "unused"]
                .filter(key => this.counts[key] > 0)
                .map(key => `${this.counts[key]} ${LABELS[key]}`)
            return `Sync links: ${parts.join(", ")}`
        },
    },
}
</script>

<style scoped>
.link-health-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    height: 1.55em;
    padding: 0 0.5em;
    border: 1px solid transparent;
    border-radius: 0.8em;
    font-size: 0.8em;
    font-weight: 600;
    line-height: 1;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    cursor: default;
}

.link-health-chip i {
    font-size: 0.85em;
}

.link-health-large {
    font-size: 0.7em;
    border-width: 2px;
}

.link-health-broken {
    color: var(--health-critical-ink);
    background: var(--health-critical-tint);
    border-color: var(--link-broken);
}

.link-health-degraded {
    color: var(--health-warning-ink);
    background: var(--health-warning-tint);
    border-color: var(--link-degraded);
}

.link-health-unknown,
.link-health-unused {
    color: #5c636a;
    background: #f1f3f5;
    border-color: var(--link-unknown);
}

.link-health-unknown {
    border-style: dashed;
}

.link-health-ok {
    color: var(--health-ok-ink);
    background: #eef8f2;
    border-color: var(--link-ok);
}
</style>
