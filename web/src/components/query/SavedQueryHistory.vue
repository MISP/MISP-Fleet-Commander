<template>
    <section class="svh" aria-labelledby="svh-title">
        <div class="svh-head">
            <div class="svh-heading">
                <h2 id="svh-title" class="svh-title">History</h2>
                <p v-if="note" class="svh-note">{{ note }}</p>
                <ul v-if="threshold && anyPoint" class="svh-legend">
                    <li>
                        <svg width="20" height="8" aria-hidden="true"><line x1="1" y1="4" x2="19" y2="4" class="svh-legend-line" /></svg>
                        {{ threshold.text }}
                    </li>
                    <li v-if="threshold.side">
                        <span :class="['svh-legend-zone', `tone-${threshold.tone}`]" aria-hidden="true"></span>
                        Not as expected
                    </li>
                </ul>
            </div>
            <div class="svh-tools">
                <span v-if="loading && history" class="svh-updating" role="status">
                    <b-spinner small class="mr-1"></b-spinner>Updating…
                </span>
                <RangePicker v-model="range"></RangePicker>
            </div>
        </div>

        <b-alert v-if="error" show variant="danger" class="svh-alert">
            Could not load the history: {{ error }}
            <b-button size="sm" variant="outline-danger" class="ml-2" @click="load">Try again</b-button>
        </b-alert>
        <div v-else-if="!history" class="svh-grid" aria-hidden="true">
            <div v-for="index in skeletons" :key="index" class="svh-card svh-skeleton"></div>
        </div>
        <div v-else-if="charts.length === 0" class="svh-empty">
            <i class="fas fa-chart-line" aria-hidden="true"></i>
            <p>It runs on no server now.</p>
        </div>
        <div v-else-if="!anyPoint" class="svh-empty">
            <i class="fas fa-chart-line" aria-hidden="true"></i>
            <p><strong>{{ emptyTitle }}</strong> {{ emptyText }}</p>
        </div>
        <template v-else>
            <div :class="['svh-grid', { 'is-loading': loading }]">
                <div v-for="chart in shown" :key="chart.serverId" class="svh-card">
                    <TimeSeriesChart
                        :title="chart.serverName"
                        :series="chart.series"
                        :from="history.from"
                        :to="history.to"
                        :interval="history.interval_s"
                        :partial-since="history.partial_since"
                        :y-domain="yDomain"
                        :threshold="chart.latest ? chartThreshold : null"
                        :height="140"
                    >
                        <!-- Its own line under the name, on every chart: the plots of a row stay level -->
                        <template #badge>
                            <span class="svh-status">
                                <span v-if="chart.meta" :class="['svh-badge', `job-tone-${chart.meta.tone}`]">
                                    <i :class="['fas', chart.meta.icon]" aria-hidden="true"></i>{{ chart.meta.label }}
                                </span>
                                <span class="svh-latest">{{ latestText(chart.latest) }}</span>
                            </span>
                        </template>
                    </TimeSeriesChart>
                </div>
            </div>
            <div v-if="hiddenCount > 0" class="svh-more">
                <b-button variant="outline-secondary" size="sm" @click="showAll = true">
                    Show all {{ charts.length }} servers
                </b-button>
                <span class="svh-more-note">{{ hiddenCount }} more, in the same order as the table</span>
            </div>
        </template>
    </section>
</template>

<script>
import RangePicker from "@/components/ui/charts/RangePicker.vue"
import TimeSeriesChart from "@/components/ui/charts/TimeSeriesChart.vue"
import api from "@/api/queries"
import { DEFAULT_RANGE, RANGES } from "@/helpers/metrics"
import { hasPoints, historyCharts, latestText, pointNote, sharedDomain, thresholdOf } from "@/helpers/queryHistory"
import { SEVERITY_TONES } from "@/helpers/savedQueries"

const SHOWN = 12
const RELOAD_DELAY = 300
const RANGE_KEY = "mfc.savedQueryHistory.range"

function rememberedRange() {
    try {
        const saved = window.localStorage.getItem(RANGE_KEY)
        return RANGES.some((range) => range.key === saved) ? saved : DEFAULT_RANGE
    } catch (error) {
        return DEFAULT_RANGE
    }
}

// What each server of a saved query answered over time: one small chart per server, all on one value axis, with
// the expectation drawn as a line and the side that misses it tinted
export default {
    name: "SavedQueryHistory",
    components: { RangePicker, TimeSeriesChart },
    props: {
        savedId: { type: Number, required: true },
        severity: { type: String, default: "warning" },
        // The saved query's servers as its page shows them, worst first: `[{ server_id, state, meta, result }]`
        states: { type: Array, default: () => [] },
    },
    data() {
        return {
            range: rememberedRange(),
            history: null,
            loading: false,
            error: null,
            showAll: false,
        }
    },
    computed: {
        threshold() {
            if (!this.history) {
                return null
            }
            const threshold = thresholdOf(this.history.expectation, this.history.expectation_text)
            return threshold && Object.assign({ tone: SEVERITY_TONES[this.severity] || "warning" }, threshold)
        },
        // Drawn on each chart that has points: the line and the tint, its words in the legend above
        chartThreshold() {
            const threshold = this.threshold
            return threshold && { value: threshold.value, side: threshold.side, tone: threshold.tone, description: threshold.text }
        },
        yDomain() {
            return this.history ? sharedDomain(this.history.servers, this.threshold) : null
        },
        charts() {
            const meta = new Map(this.states.map((entry) => [entry.server_id, entry.meta]))
            return historyCharts(this.history, this.states.map((entry) => entry.server_id))
                .map((chart) => Object.assign({ meta: meta.get(chart.serverId) || null }, chart))
        },
        shown() {
            return this.showAll ? this.charts : this.charts.slice(0, SHOWN)
        },
        hiddenCount() {
            return this.charts.length - this.shown.length
        },
        anyPoint() {
            return hasPoints(this.history)
        },
        note() {
            return this.anyPoint ? pointNote(this.history) : ""
        },
        everAnswered() {
            return this.states.some((entry) => entry.result)
        },
        emptyTitle() {
            return this.everAnswered ? "Nothing over this range." : "No history yet."
        },
        emptyText() {
            return this.everAnswered
                ? "No server answered with a number over this range: see each server's last answer above, or pick a longer range."
                : "Each run adds a point for each of its servers."
        },
        skeletons() {
            return Math.min(Math.max(this.states.length, 1), 2)
        },
        // Changes when a server's last answer does: a run has added points
        answeredAt() {
            return this.states.map((entry) => (entry.result ? entry.result.checked_at : 0)).join(",")
        },
    },
    watch: {
        savedId() {
            this.history = null
            this.showAll = false
            this.load()
        },
        range(range) {
            try {
                window.localStorage.setItem(RANGE_KEY, range)
            } catch (error) {
                // Only a convenience: the range is still applied
            }
            this.load()
        },
        answeredAt() {
            clearTimeout(this.reloadTimer)
            this.reloadTimer = setTimeout(this.load, RELOAD_DELAY)
        },
    },
    created() {
        this.load()
    },
    beforeDestroy() {
        clearTimeout(this.reloadTimer)
    },
    methods: {
        latestText,
        load() {
            const asked = { id: this.savedId, range: this.range }
            this.loading = true
            return api.savedHistory(asked.id, asked.range).then((history) => {
                if (asked.id === this.savedId && asked.range === this.range) {
                    this.history = history
                    this.error = null
                }
            }).catch((error) => {
                if (asked.id === this.savedId && asked.range === this.range) {
                    this.error = String(error)
                }
            }).finally(() => {
                if (asked.id === this.savedId && asked.range === this.range) {
                    this.loading = false
                }
            })
        },
    },
}
</script>

<style scoped>
.svh {
    margin-top: 1.5rem;
}

.svh-head {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 0.5rem 1rem;
    margin-bottom: 0.6rem;
}

.svh-heading {
    min-width: 0;
}

.svh-title {
    margin: 0;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #5a6270;
}

.svh-note {
    margin: 0.2rem 0 0;
    max-width: 52rem;
    color: #6c757d;
    font-size: 0.8rem;
    line-height: 1.45;
}

.svh-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.15rem 1rem;
    margin: 0.3rem 0 0;
    padding: 0;
    list-style: none;
    color: #52514e;
    font-size: 0.8rem;
}

.svh-legend li {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
}

.svh-legend-line {
    stroke: #52514e;
    stroke-width: 1;
    stroke-dasharray: 4 3;
}

.svh-legend-zone {
    display: inline-block;
    width: 14px;
    height: 10px;
    border-radius: 2px;
    background: rgba(255, 193, 7, 0.22);
}

.svh-legend-zone.tone-critical {
    background: rgba(220, 53, 69, 0.16);
}

.svh-legend-zone.tone-info {
    background: rgba(23, 162, 184, 0.18);
}

.svh-tools {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.svh-updating {
    color: #6c757d;
    font-size: 0.8rem;
    white-space: nowrap;
}

.svh-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
    gap: 0.75rem;
    transition: opacity 0.15s ease;
}

.svh-grid.is-loading {
    opacity: 0.6;
}

.svh-card {
    min-width: 0;
    padding: 0.6rem 0.75rem 0.5rem;
    border: 1px solid #e4e7ec;
    border-radius: 6px;
    background: #fff;
}

.svh-skeleton {
    height: 196px;
    border: 0;
    background: linear-gradient(90deg, #f0f2f5 25%, #e6e9ee 37%, #f0f2f5 63%);
    background-size: 400% 100%;
    animation: svh-shimmer 1.4s ease infinite;
}

@keyframes svh-shimmer {
    0% { background-position: 100% 50%; }
    100% { background-position: 0 50%; }
}

@media (prefers-reduced-motion: reduce) {
    .svh-skeleton {
        animation: none;
    }
}

.svh-status {
    order: 3;
    flex-basis: 100%;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.2rem 0.5rem;
    min-width: 0;
}

.svh-latest {
    color: #6c757d;
    font-size: 0.78rem;
    font-variant-numeric: tabular-nums;
}

.svh-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.02rem 0.5rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    white-space: nowrap;
    color: var(--job-ink);
    background: var(--job-tint);
}

.svh-empty {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem 1.1rem;
    border: 1px dashed #d5dbe3;
    border-radius: 6px;
    background: #fafbfc;
    color: #52514e;
    font-size: 0.85rem;
}

.svh-empty > i {
    color: #9aa6b5;
    font-size: 1.25rem;
}

.svh-empty p {
    margin: 0;
}

.svh-more {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem 0.75rem;
    margin-top: 0.75rem;
}

.svh-more-note {
    color: #6c757d;
    font-size: 0.8rem;
}

.svh-alert {
    font-size: 0.875rem;
}
</style>
