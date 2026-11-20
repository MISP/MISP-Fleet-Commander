<template>
    <div class="qhg">
        <div :class="['qhg-grid', { 'is-loading': loading }]" :style="gridStyle">
            <div v-for="chart in shown" :key="chart.serverId" class="qhg-card">
                <TimeSeriesChart
                    :title="chart.serverName"
                    :series="chart.series"
                    :from="history.from"
                    :to="history.to"
                    :interval="history.interval_s"
                    :partial-since="history.partial_since"
                    :y-domain="yDomain"
                    :threshold="chart.latest ? chartThreshold : null"
                    :height="height"
                >
                    <!-- Its own line under the name, on every chart: the plots of a row stay level -->
                    <template #badge>
                        <span class="qhg-status">
                            <span v-if="chart.meta" :class="['qhg-badge', `job-tone-${chart.meta.tone}`]">
                                <i :class="['fas', chart.meta.icon]" aria-hidden="true"></i>{{ chart.meta.label }}
                            </span>
                            <span class="qhg-latest">{{ latestText(chart.latest) }}</span>
                        </span>
                    </template>
                </TimeSeriesChart>
            </div>
        </div>
        <div v-if="hiddenCount > 0" class="qhg-more">
            <b-button variant="outline-secondary" size="sm" @click="showAll = true">
                Show all {{ charts.length }} servers
            </b-button>
            <span class="qhg-more-note">{{ hiddenCount }} more{{ moreNote ? `, ${moreNote}` : "" }}</span>
        </div>
    </div>
</template>

<script>
import TimeSeriesChart from "@/components/ui/charts/TimeSeriesChart.vue"
import { historyCharts, latestText, sharedDomain } from "@/helpers/queryHistory"

// One small chart per server of a saved query's history, all on one value axis, with the expectation drawn as a
// line and the side that misses it tinted: on the saved query's page and in the widgets of a fleet's Usage tab
export default {
    name: "QueryHistoryGrid",
    components: { TimeSeriesChart },
    props: {
        // As `GET /queries/saved/<id>/history` gives it
        history: { type: Object, required: true },
        // `{ value, text, side, tone }`, or null without an expectation to draw
        threshold: { type: Object, default: null },
        // The servers in the order to draw them, worst first: `[{ server_id, meta }]`
        states: { type: Array, default: () => [] },
        // Charts shown before "Show all"
        limit: { type: Number, default: 12 },
        height: { type: Number, default: 140 },
        // Narrowest a chart gets before the grid drops a column
        minWidth: { type: Number, default: 300 },
        loading: { type: Boolean, default: false },
        // After "N more": in which order they come
        moreNote: { type: String, default: "" },
    },
    data() {
        return { showAll: false }
    },
    computed: {
        // Drawn on each chart that has points: the line and the tint, its words in a legend above
        chartThreshold() {
            const threshold = this.threshold
            return threshold && { value: threshold.value, side: threshold.side, tone: threshold.tone, description: threshold.text }
        },
        yDomain() {
            return sharedDomain(this.history.servers, this.threshold)
        },
        charts() {
            const meta = new Map(this.states.map((entry) => [entry.server_id, entry.meta]))
            return historyCharts(this.history, this.states.map((entry) => entry.server_id))
                .map((chart) => Object.assign({ meta: meta.get(chart.serverId) || null }, chart))
        },
        shown() {
            return this.showAll ? this.charts : this.charts.slice(0, this.limit)
        },
        hiddenCount() {
            return this.charts.length - this.shown.length
        },
        gridStyle() {
            return { gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, ${this.minWidth}px), 1fr))` }
        },
    },
    methods: {
        latestText,
    },
}
</script>

<style scoped>
.qhg-grid {
    display: grid;
    gap: 0.75rem;
    transition: opacity 0.15s ease;
}

.qhg-grid.is-loading {
    opacity: 0.6;
}

.qhg-card {
    min-width: 0;
    padding: 0.6rem 0.75rem 0.5rem;
    border: 1px solid #e4e7ec;
    border-radius: 6px;
    background: #fff;
}

.qhg-status {
    order: 3;
    flex-basis: 100%;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.2rem 0.5rem;
    min-width: 0;
}

.qhg-latest {
    color: #6c757d;
    font-size: 0.78rem;
    font-variant-numeric: tabular-nums;
}

.qhg-badge {
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

.qhg-more {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem 0.75rem;
    margin-top: 0.75rem;
}

.qhg-more-note {
    color: #6c757d;
    font-size: 0.8rem;
}
</style>
