<template>
    <span class="server-health">
        <template v-if="issues.length > 0">
            <router-link
                ref="badge"
                :to="attentionLink"
                :class="['health-badge', `sev-${worst}`]"
                :aria-label="ariaLabel"
            >
                <i :class="[severityMeta[worst].icon, 'health-badge-icon']" aria-hidden="true"></i>
                <span class="health-badge-count">{{ issues.length }}</span>
            </router-link>
            <b-tooltip
                :target="() => $refs.badge && $refs.badge.$el"
                triggers="hover focus"
                placement="right"
                boundary="window"
                custom-class="health-tooltip"
            >
                <div class="health-tooltip-head">{{ countsLabel }}</div>
                <ul class="health-tooltip-list">
                    <li v-for="issue in shownIssues" :key="issue.id" :class="`sev-${issue.severity}`">
                        <i :class="[severityMeta[issue.severity].icon, 'fa-fw']" aria-hidden="true"></i>
                        <span>{{ issue.title }}</span>
                    </li>
                </ul>
                <div v-if="hiddenCount > 0" class="health-tooltip-foot">and {{ hiddenCount }} more</div>
                <div v-if="ackedCount > 0" class="health-tooltip-foot">
                    {{ ackedCount }} acknowledged {{ ackedCount === 1 ? "issue" : "issues" }} not shown
                </div>
            </b-tooltip>
        </template>
        <span
            v-else-if="loaded"
            class="health-ok"
            :title="ackedCount > 0 ? `No issues (${ackedCount} acknowledged)` : 'No issues'"
        >
            <i class="fas fa-check" aria-hidden="true"></i>
            <span class="sr-only">No issues</span>
        </span>
        <span v-else class="health-unknown" title="Health not loaded yet">
            <span aria-hidden="true">–</span>
            <span class="sr-only">Health not loaded yet</span>
        </span>
    </span>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import { SEVERITY_META, countsText } from "@/views/attention/healthLabels"
import { emptyCounts } from "@/store/modules/health"

const MAX_LISTED = 6

export default {
    name: "ServerHealthBadge",
    props: {
        server_id: { type: Number, required: true },
        fleet_id: { type: [Number, String], default: null },
    },
    data() {
        return {
            severityMeta: SEVERITY_META,
        }
    },
    computed: {
        ...mapState({
            loaded: state => state.health.loaded,
            issuesByServer: state => state.health.issuesByServer,
        }),
        ...mapGetters({
            serverActiveIssues: "health/serverActiveIssues",
        }),
        issues() {
            return this.serverActiveIssues[this.server_id] || []
        },
        ackedCount() {
            return (this.issuesByServer[this.server_id] || []).length - this.issues.length
        },
        worst() {
            return this.issues.length > 0 ? this.issues[0].severity : null
        },
        shownIssues() {
            return this.issues.slice(0, MAX_LISTED)
        },
        hiddenCount() {
            return this.issues.length - this.shownIssues.length
        },
        countsLabel() {
            const counts = emptyCounts()
            this.issues.forEach((issue) => { counts[issue.severity] += 1 })
            return countsText(counts)
        },
        ariaLabel() {
            return `${this.countsLabel}. Show in Needs attention`
        },
        attentionLink() {
            const query = { server_id: String(this.server_id) }
            if (this.fleet_id !== null) {
                query.fleet_id = String(this.fleet_id)
            }
            return { name: "attention", query }
        },
    },
}
</script>

<style scoped>
.server-health {
    display: inline-flex;
    align-items: center;
    min-width: 2.75rem;
}

.health-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    height: 1.4rem;
    padding: 0 0.45rem;
    border: 1px solid transparent;
    border-radius: 0.7rem;
    font-size: 0.75rem;
    font-weight: 600;
    line-height: 1;
    font-variant-numeric: tabular-nums;
    text-decoration: none;
    white-space: nowrap;
    transition: filter 0.15s ease;
}

.health-badge:hover,
.health-badge:focus {
    text-decoration: none;
    filter: brightness(0.95);
}

.health-badge:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 2px;
}

.health-badge.sev-critical {
    color: var(--health-critical-ink);
    background: var(--health-critical-tint);
    border-color: var(--health-critical);
}

.health-badge.sev-warning {
    color: var(--health-warning-ink);
    background: var(--health-warning-tint);
    border-color: var(--health-warning);
}

.health-badge.sev-info {
    color: var(--health-info-ink);
    background: var(--health-info-tint);
    border-color: var(--health-info);
}

.health-ok {
    color: var(--health-ok-ink);
    padding-left: 0.5rem;
    opacity: 0.8;
}

.health-unknown {
    color: #adb5bd;
    padding-left: 0.6rem;
}
</style>

<style>
/* The tooltip is rendered at the end of <body>: not scoped */
.health-tooltip .tooltip-inner {
    max-width: 320px;
    padding: 0.5rem 0.65rem;
    text-align: left;
}

.health-tooltip-head {
    font-weight: 600;
    margin-bottom: 0.3rem;
}

.health-tooltip-list {
    list-style: none;
    margin: 0;
    padding: 0;
}

.health-tooltip-list li {
    display: flex;
    gap: 0.35rem;
    align-items: baseline;
    line-height: 1.35;
    padding: 0.1rem 0;
}

.health-tooltip-list li.sev-critical i { color: #ff8a95; }
.health-tooltip-list li.sev-warning i { color: #ffd451; }
.health-tooltip-list li.sev-info i { color: #6fd3e3; }

.health-tooltip-foot {
    margin-top: 0.3rem;
    opacity: 0.75;
    font-size: 0.85em;
}
</style>
