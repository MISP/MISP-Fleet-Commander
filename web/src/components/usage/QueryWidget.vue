<template>
    <article :class="['qw', `is-${widget.display}`, `is-${span}`]" :aria-labelledby="`qw-name-${widget.id}`">
        <header class="qw-head">
            <div class="qw-heading">
                <h4 :id="`qw-name-${widget.id}`" class="qw-name">
                    <router-link v-if="saved" :to="savedLink">{{ saved.name }}</router-link>
                    <span v-else>Deleted saved query</span>
                </h4>
                <p v-if="facts" class="qw-facts">{{ facts }}</p>
            </div>
            <div class="qw-tools">
                <span v-if="loading && history" class="qw-updating" role="status">
                    <b-spinner small></b-spinner><span class="sr-only">Updating…</span>
                </span>
                <b-dropdown
                    size="sm"
                    variant="link"
                    right
                    no-caret
                    :disabled="busy"
                    toggle-class="qw-menu"
                    :aria-label="`Options for ${saved ? saved.name : 'this widget'}`"
                >
                    <template #button-content>
                        <i class="fas fa-ellipsis-v" aria-hidden="true"></i><span class="sr-only">Options</span>
                    </template>
                    <b-dropdown-header>Show as</b-dropdown-header>
                    <b-dropdown-item-button
                        v-for="option in DISPLAYS"
                        :key="option.key"
                        :active="widget.display === option.key"
                        @click="$emit('display', option.key)"
                    >
                        <i :class="['fas', 'fa-fw', option.icon, 'mr-1']" aria-hidden="true"></i>{{ option.label }}
                    </b-dropdown-item-button>
                    <b-dropdown-divider></b-dropdown-divider>
                    <b-dropdown-item-button :disabled="first" @click="$emit('move', -1)">
                        <i class="fas fa-fw fa-arrow-up mr-1" aria-hidden="true"></i>Move up
                    </b-dropdown-item-button>
                    <b-dropdown-item-button :disabled="last" @click="$emit('move', 1)">
                        <i class="fas fa-fw fa-arrow-down mr-1" aria-hidden="true"></i>Move down
                    </b-dropdown-item-button>
                    <b-dropdown-divider></b-dropdown-divider>
                    <b-dropdown-item v-if="saved" :to="savedLink">
                        <i class="fas fa-fw fa-external-link-alt mr-1" aria-hidden="true"></i>Open the saved query
                    </b-dropdown-item>
                    <b-dropdown-item-button variant="danger" @click="$emit('remove')">
                        <i class="fas fa-fw fa-times mr-1" aria-hidden="true"></i>Remove from this tab
                    </b-dropdown-item-button>
                </b-dropdown>
            </div>
        </header>

        <ul v-if="standing.length" class="qw-standing" :aria-label="serverId === null ? 'How this fleet\'s servers last answered' : 'How the server last answered'">
            <li v-for="part in standing" :key="part.state" :class="['qw-chip', `job-tone-${part.tone}`]">
                <i :class="['fas', part.icon]" aria-hidden="true"></i>{{ part.text }}
            </li>
        </ul>

        <div v-if="problem" class="qw-message is-muted">
            <i class="fas fa-fw fa-info-circle" aria-hidden="true"></i>
            <span>
                {{ problem }}
                <router-link v-if="saved" :to="savedLink">Open the saved query</router-link>
                <template v-if="saved">{{ serverId === null ? " to change it, or remove this widget." : " to change that." }}</template>
            </span>
        </div>

        <div v-else-if="error" class="qw-message is-critical" role="alert">
            <i class="fas fa-fw fa-exclamation-triangle" aria-hidden="true"></i>
            <span>
                Could not load its history: {{ error }}
                <button type="button" class="btn btn-link qw-retry" @click="load">Try again</button>
            </span>
        </div>

        <div v-else-if="!history" class="qw-skeleton" aria-hidden="true"></div>

        <div v-else-if="!anyPoint" class="qw-message is-empty">
            <i class="fas fa-fw fa-chart-line" aria-hidden="true"></i>
            <span>{{ emptyText }}</span>
        </div>

        <div v-else-if="widget.display === 'total'" :class="['qw-body', 'qw-total', { 'is-loading': loading }]">
            <div class="qw-summary">
                <div class="qw-figure">
                    <span class="qw-value" :title="latestTitle">{{ valueText }}</span>
                    <span v-if="deltaText" class="qw-delta">
                        <i v-if="deltaIcon" :class="['fas', deltaIcon]" aria-hidden="true"></i>{{ deltaText }}
                        <span class="qw-delta-range">{{ rangePhrase }}</span>
                    </span>
                </div>
                <p v-if="reporting" class="qw-reporting">{{ reporting }}</p>
                <p v-if="carried" class="qw-carried" :title="carried.title">
                    <i class="fas fa-history" aria-hidden="true"></i>
                    <span>{{ carried.text }}<span class="sr-only">. {{ carried.title }}</span></span>
                </p>
            </div>
            <div class="qw-chart">
                <TimeSeriesChart
                    :title="totalTitle"
                    :subtitle="totalSubtitle"
                    :series="total.series"
                    :from="history.total.from"
                    :to="history.total.to"
                    :interval="history.total.interval_s"
                    :partial-since="history.total.partial_since"
                    :zero="totalFromZero"
                    :height="150"
                ></TimeSeriesChart>
            </div>
            <p class="qw-note">{{ totalNote }}</p>
        </div>

        <div v-else :class="['qw-body', { 'is-loading': loading }]">
            <div v-if="threshold || pointNote" class="qw-servers-head">
                <ThresholdLegend v-if="threshold" :threshold="threshold"></ThresholdLegend>
                <p v-if="pointNote" class="qw-note">{{ pointNote }}</p>
            </div>
            <QueryHistoryGrid
                :key="widget.saved_query ? widget.saved_query.id : 0"
                :history="history"
                :threshold="threshold"
                :states="states"
                :limit="SHOWN_SERVERS"
                :height="120"
                :min-width="360"
                :loading="loading"
                more-note="worst first"
            ></QueryHistoryGrid>
        </div>
    </article>
</template>

<script>
import api from "@/api/usageWidgets"
import QueryHistoryGrid from "@/components/query/QueryHistoryGrid.vue"
import ThresholdLegend from "@/components/query/ThresholdLegend.vue"
import TimeSeriesChart from "@/components/ui/charts/TimeSeriesChart.vue"
import { formatValue } from "@/helpers/metrics"
import { hasPoints, pointNote, thresholdOf } from "@/helpers/queryHistory"
import { SEVERITY_TONES, serversWorstFirst } from "@/helpers/savedQueries"
import {
    carriedText, changeText, DISPLAYS, problemText, reportingText, SHOWN_SERVERS, standingParts, totalNote,
    totalValueText, totalView, widgetFacts,
} from "@/helpers/usageWidgets"

// One saved query followed on a fleet's Usage tab: the fleet's servers' answers over the tab's range, summed or
// server by server, or only one server's when the tab is limited to it
export default {
    name: "QueryWidget",
    components: { QueryHistoryGrid, ThresholdLegend, TimeSeriesChart },
    props: {
        fleetId: { type: Number, required: true },
        // The server the tab is limited to, or null for all of them
        serverId: { type: Number, default: null },
        serverName: { type: String, default: "" },
        // As `GET /fleets/<id>/widgets` gives it
        widget: { type: Object, required: true },
        rangeKey: { type: String, required: true },
        // `over the last 7 days`
        rangePhrase: { type: String, default: "" },
        // Changes when a query run ended: its answers may have added points
        refreshKey: { type: Number, default: 0 },
        // On a wide screen: half a row (two Fleet totals side by side) or the whole of it
        span: { type: String, default: "full" },
        first: { type: Boolean, default: false },
        last: { type: Boolean, default: false },
        busy: { type: Boolean, default: false },
    },
    data() {
        return {
            DISPLAYS,
            SHOWN_SERVERS,
            history: null,
            loading: false,
            error: null,
        }
    },
    computed: {
        saved() {
            return this.widget.saved_query
        },
        savedLink() {
            return { name: "query.saved.view", params: { saved_id: String(this.saved.id) } }
        },
        facts() {
            return widgetFacts(this.saved)
        },
        severity() {
            return (this.saved && this.saved.severity) || "warning"
        },
        standing() {
            return this.saved && this.saved.expectation_text ? standingParts(this.widget.servers, this.severity) : []
        },
        states() {
            return serversWorstFirst(this.widget.servers, this.severity)
        },
        problem() {
            if (!this.saved) {
                return "Its saved query was deleted."
            }
            return problemText(this.widget.problem, this.serverId === null ? "" : this.serverName)
        },
        anyPoint() {
            return hasPoints(this.history)
        },
        emptyText() {
            const answered = (this.widget.servers || []).some((entry) => entry.result)
            if (!answered) {
                return "No history yet: each run of the saved query adds a point."
            }
            return this.serverId === null
                ? `No server of this fleet answered with a number ${this.rangePhrase}: pick a longer range, or see each server's last answer on the saved query's page.`
                : `${this.serverName} did not answer with a number ${this.rangePhrase}: pick a longer range, or see its last answer on the saved query's page.`
        },
        threshold() {
            if (!this.history) {
                return null
            }
            const threshold = thresholdOf(this.history.expectation, this.history.expectation_text)
            return threshold && Object.assign({ tone: SEVERITY_TONES[this.severity] || "warning" }, threshold)
        },
        pointNote() {
            return pointNote(this.history)
        },
        total() {
            return totalView(this.history)
        },
        valueText() {
            return totalValueText(this.total && this.total.latest)
        },
        latestTitle() {
            const latest = this.total && this.total.latest
            const label = this.serverId === null ? "Latest total" : "Latest answer"
            return latest ? `${label}: ${formatValue(latest.value, "count", { exact: true })}` : null
        },
        deltaText() {
            return changeText(this.total && this.total.change)
        },
        deltaIcon() {
            const change = this.total && this.total.change
            if (!change || change.abs === 0) {
                return ""
            }
            return change.abs > 0 ? "fa-arrow-up" : "fa-arrow-down"
        },
        reporting() {
            return reportingText(this.total)
        },
        carried() {
            return carriedText(this.history)
        },
        // The axis hugs the total so that a count moving around 2,000 reads as moving; with a single value there is
        // nothing to hug, and it starts at 0
        totalFromZero() {
            const values = new Set((this.total ? this.total.series[0].points : []).map((point) => point[1]))
            return values.size < 2
        },
        totalTitle() {
            const select = this.history && this.history.kind === "select"
            if (this.serverId !== null) {
                return select ? "Rows on the server" : "The server's answer"
            }
            return select ? "Rows on the fleet" : "Fleet total"
        },
        totalSubtitle() {
            const servers = this.total ? this.total.servers : 0
            const per = this.history && this.history.total.tier === "day" ? "per day" : "per hour"
            if (this.serverId !== null) {
                return `its last answer ${per}`
            }
            return `${servers} server${servers === 1 ? "" : "s"} summed, ${per}`
        },
        totalNote() {
            return totalNote(this.history, { single: this.serverId !== null })
        },
    },
    watch: {
        rangeKey() {
            this.load()
        },
        serverId() {
            this.load()
        },
        refreshKey() {
            this.load()
        },
        "widget.saved_query.id"() {
            this.history = null
            this.load()
        },
        "widget.problem"(problem, previous) {
            if (!problem && previous) {
                this.load()
            }
        },
    },
    created() {
        this.load()
    },
    methods: {
        load() {
            if (this.problem) {
                return Promise.resolve()
            }
            const asked = { widget: this.widget.id, range: this.rangeKey, server: this.serverId }
            const current = () => asked.widget === this.widget.id && asked.range === this.rangeKey
                && asked.server === this.serverId
            this.loading = true
            return api.history(this.fleetId, this.widget.id, this.rangeKey, this.serverId).then((history) => {
                if (current()) {
                    this.history = history
                    this.error = null
                }
            }).catch((error) => {
                if (current()) {
                    this.error = String(error)
                }
            }).finally(() => {
                if (current()) {
                    this.loading = false
                }
            })
        },
    },
}
</script>

<style scoped>
.qw {
    min-width: 0;
    padding: 0.7rem 0.85rem 0.75rem;
    border: 1px solid #e4e7ec;
    border-radius: 6px;
    background: #fff;
}

.qw-head {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
}

.qw-heading {
    flex: 1;
    min-width: 0;
}

.qw-name {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
    line-height: 1.3;
    overflow-wrap: anywhere;
}

.qw-name a {
    color: #212d40;
}

.qw-name a:hover,
.qw-name a:focus {
    color: var(--primary, #007bff);
}

.qw-facts {
    margin: 0.1rem 0 0;
    color: #6c757d;
    font-size: 0.78rem;
}

.qw-tools {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    margin: -0.2rem -0.45rem 0 0;
}

.qw-updating {
    color: #6c757d;
}

.qw-tools ::v-deep .qw-menu {
    padding: 0.15rem 0.5rem;
    color: #5a6270;
}

.qw-tools ::v-deep .qw-menu:hover,
.qw-tools ::v-deep .qw-menu:focus {
    color: #212d40;
}

.qw-standing {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin: 0.45rem 0 0;
    padding: 0;
    list-style: none;
}

.qw-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.05rem 0.5rem;
    border-radius: 999px;
    color: var(--job-ink);
    background: var(--job-tint);
    font-size: 0.72rem;
    font-weight: 700;
    white-space: nowrap;
}

.qw-body {
    margin-top: 0.6rem;
    transition: opacity 0.15s ease;
}

.qw-body.is-loading {
    opacity: 0.6;
}

.qw-figure {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.15rem 0.65rem;
}

.qw-value {
    font-size: 1.6rem;
    font-weight: 700;
    line-height: 1.1;
    color: #212d40;
    font-variant-numeric: tabular-nums;
}

.qw-delta {
    color: #52514e;
    font-size: 0.8rem;
    font-variant-numeric: tabular-nums;
}

.qw-delta i {
    margin-right: 0.25rem;
    font-size: 0.7rem;
    color: #6c757d;
}

.qw-delta-range {
    color: #6c757d;
}

.qw-reporting {
    margin: 0.15rem 0 0;
    color: var(--health-warning-ink);
    font-size: 0.78rem;
}

.qw-carried {
    display: flex;
    align-items: baseline;
    gap: 0.35rem;
    margin: 0.2rem 0 0;
    color: #5b6470;
    font-size: 0.78rem;
    line-height: 1.35;
    cursor: help;
}

/* The tone of the "could not run" chip it explains */
.qw-carried .fa-history {
    flex: none;
    color: var(--health-info-ink);
    font-size: 0.72rem;
}

.qw-chart {
    margin-top: 0.5rem;
}

/* A Fleet total alone in its row: its figure beside the chart rather than above a chart twice as wide as high */
@media (min-width: 1100px) {
    .qw.is-full .qw-total {
        display: grid;
        grid-template-columns: minmax(11rem, 15rem) minmax(0, 1fr);
        grid-template-areas: "summary chart" "note chart";
        grid-template-rows: auto 1fr;
        column-gap: 1.5rem;
    }

    .qw.is-full .qw-summary {
        grid-area: summary;
        padding-top: 0.35rem;
    }

    .qw.is-full .qw-figure {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.3rem;
    }

    .qw.is-full .qw-chart {
        grid-area: chart;
        margin-top: 0;
    }

    .qw.is-full .qw-total .qw-note {
        grid-area: note;
        margin-top: 0.6rem;
    }
}

.qw-note {
    margin: 0.35rem 0 0;
    color: #6c757d;
    font-size: 0.75rem;
    line-height: 1.45;
}

.qw-servers-head {
    margin-bottom: 0.55rem;
}

.qw-servers-head .qw-note {
    margin-top: 0.2rem;
}

.qw-message {
    display: flex;
    align-items: baseline;
    gap: 0.45rem;
    margin-top: 0.6rem;
    padding: 0.55rem 0.7rem;
    border-radius: 4px;
    font-size: 0.8125rem;
    line-height: 1.5;
}

.qw-message.is-muted {
    border-left: 3px solid #9aa1a7;
    background: #f8f9fb;
    color: #52514e;
}

.qw-message.is-critical {
    border-left: 3px solid var(--health-critical);
    background: var(--health-critical-tint);
}

.qw-message.is-empty {
    border: 1px dashed #d5dbe3;
    background: #fafbfc;
    color: #52514e;
}

.qw-message > i {
    color: #9aa6b5;
}

.qw-retry {
    padding: 0;
    margin-left: 0.3rem;
    font-size: inherit;
    font-weight: 600;
    vertical-align: baseline;
}

.qw-skeleton {
    height: 13rem;
    margin-top: 0.6rem;
    border-radius: 6px;
    background: linear-gradient(90deg, #f0f2f5 25%, #e6e9ee 37%, #f0f2f5 63%);
    background-size: 400% 100%;
    animation: qw-shimmer 1.4s ease infinite;
}

@keyframes qw-shimmer {
    0% { background-position: 100% 50%; }
    100% { background-position: 0 50%; }
}

@media (prefers-reduced-motion: reduce) {
    .qw-skeleton {
        animation: none;
    }

    .qw-body {
        transition: none;
    }
}
</style>
