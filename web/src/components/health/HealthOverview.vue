<template>
    <section v-if="visible" class="health-overview" aria-label="Fleet health">
        <div class="overview-heading">
            <span :class="['overview-mark', markClass]" aria-hidden="true">
                <i :class="markIcon"></i>
            </span>
            <div class="overview-text">
                <h2 class="overview-title">Fleet health</h2>
                <p class="overview-subtitle" aria-live="polite">
                    <template v-if="!loaded && loading">
                        <b-spinner small class="mr-1"></b-spinner>Checking your servers
                    </template>
                    <template v-else-if="!loaded && error">
                        Could not load the health of your servers.
                        <b-button variant="link" size="sm" class="p-0 align-baseline" @click="reload">Try again</b-button>
                    </template>
                    <template v-else>
                        <strong>{{ healthyCount }}</strong> of {{ serverCount }} {{ serverCount === 1 ? "server" : "servers" }} healthy<span v-if="newestRefresh" :title="newestRefreshTitle"> · last refresh {{ newestRefreshText }}</span>
                    </template>
                </p>
            </div>
        </div>

        <ul v-if="loaded" class="overview-counts">
            <li
                v-for="severity in severities"
                :key="severity"
                :class="['overview-count', `sev-${severity}`, { empty: counts[severity] === 0 }]"
            >
                <i :class="[severityMeta[severity].icon, 'overview-count-icon']" aria-hidden="true"></i>
                <span class="overview-count-value">{{ counts[severity] }}</span>
                <span class="overview-count-label">{{ counts[severity] === 1 ? severityMeta[severity].label.toLowerCase() : severityMeta[severity].plural }}</span>
            </li>
        </ul>

        <b-button
            v-if="loaded"
            :to="{ name: 'attention' }"
            size="sm"
            :variant="attentionCount > 0 ? 'primary' : 'outline-primary'"
            class="overview-link"
        >
            {{ attentionCount > 0 ? "Review issues" : "Needs attention" }}<i class="fas fa-arrow-right ml-2" aria-hidden="true"></i>
        </b-button>
    </section>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import moment from "moment"
import { SEVERITIES } from "@/store/modules/health"
import { SEVERITY_META } from "@/views/attention/healthLabels"

const NOW_TICK_MS = 30 * 1000

export default {
    name: "HealthOverview",
    data() {
        return {
            severities: SEVERITIES,
            severityMeta: SEVERITY_META,
            now: Math.floor(Date.now() / 1000),
            nowTimer: null,
        }
    },
    computed: {
        ...mapState({
            summary: state => state.health.summary,
            loaded: state => state.health.loaded,
            loading: state => state.health.loading,
            error: state => state.health.error,
        }),
        ...mapGetters({
            counts: "health/counts",
            attentionCount: "health/attentionCount",
            serverWorst: "health/serverWorst",
        }),
        serverCount() {
            return this.summary ? this.summary.server_count : 0
        },
        // Hidden until there is something to say: no servers means the fleet list shows how to start
        visible() {
            return !this.loaded || this.serverCount > 0
        },
        unhealthyCount() {
            const servers = (this.summary && this.summary.servers) || {}
            return Object.keys(servers).filter(server_id => this.serverWorst[server_id]).length
        },
        healthyCount() {
            return Math.max(0, this.serverCount - this.unhealthyCount)
        },
        markClass() {
            if (!this.loaded) {
                return "mark-neutral"
            }
            if (this.counts.critical > 0) {
                return "sev-critical"
            }
            if (this.counts.warning > 0) {
                return "sev-warning"
            }
            return "mark-ok"
        },
        markIcon() {
            if (this.loaded && this.counts.critical > 0) {
                return SEVERITY_META.critical.icon
            }
            if (this.loaded && this.counts.warning > 0) {
                return SEVERITY_META.warning.icon
            }
            return this.loaded ? "fas fa-check" : "fas fa-heart-pulse"
        },
        newestRefresh() {
            return this.summary ? this.summary.newest_refresh : null
        },
        newestRefreshText() {
            return moment.unix(this.newestRefresh).from(moment.unix(Math.max(this.now, this.newestRefresh)))
        },
        newestRefreshTitle() {
            return moment.unix(this.newestRefresh).format("LLL")
        },
    },
    methods: {
        reload() {
            this.$store.dispatch("health/fetch")
        },
    },
    mounted() {
        this.$store.dispatch("health/init")
        this.nowTimer = setInterval(() => {
            this.now = Math.floor(Date.now() / 1000)
        }, NOW_TICK_MS)
    },
    beforeDestroy() {
        clearInterval(this.nowTimer)
    },
}
</script>

<style scoped>
.health-overview {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem 1.5rem;
    padding: 0.85rem 1rem;
    background: #fff;
    border: 1px solid var(--health-rule);
    border-radius: 0.5rem;
}

.overview-heading {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex: 1 1 16rem;
    min-width: 0;
}

.overview-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 2.25rem;
    height: 2.25rem;
    border-radius: 50%;
    font-size: 1rem;
}

.overview-mark.sev-critical { color: var(--health-critical-ink); background: var(--health-critical-tint); }
.overview-mark.sev-warning { color: var(--health-warning-ink); background: var(--health-warning-tint); }
.overview-mark.mark-ok { color: var(--health-ok-ink); background: #e8f5ed; }
.overview-mark.mark-neutral { color: #6c757d; background: #f1f3f5; }

.overview-title {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
}

.overview-subtitle {
    margin: 0;
    color: #6c757d;
    font-size: 0.875rem;
}

.overview-subtitle strong {
    color: #212529;
}

.overview-counts {
    display: flex;
    gap: 0.5rem;
    margin: 0;
    padding: 0;
    list-style: none;
}

.overview-count {
    display: inline-flex;
    align-items: baseline;
    gap: 0.35rem;
    padding: 0.3rem 0.65rem;
    border: 1px solid var(--health-rule);
    border-radius: 0.4rem;
    font-size: 0.875rem;
    white-space: nowrap;
}

.overview-count-value {
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}

.overview-count-label {
    color: #6c757d;
}

.overview-count.sev-critical .overview-count-icon { color: var(--health-critical-ink); }
.overview-count.sev-warning .overview-count-icon { color: var(--health-warning-ink); }
.overview-count.sev-info .overview-count-icon { color: var(--health-info-ink); }

.overview-count.sev-critical:not(.empty) { background: var(--health-critical-tint); border-color: var(--health-critical); }
.overview-count.sev-warning:not(.empty) { background: var(--health-warning-tint); border-color: var(--health-warning); }
.overview-count.sev-info:not(.empty) { background: var(--health-info-tint); border-color: var(--health-info); }

.overview-count.empty .overview-count-icon,
.overview-count.empty .overview-count-value {
    color: #adb5bd;
}

.overview-link {
    white-space: nowrap;
}

@media (max-width: 575.98px) {
    .overview-counts {
        flex-wrap: wrap;
    }
    .overview-link {
        width: 100%;
    }
}
</style>
