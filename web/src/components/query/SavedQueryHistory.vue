<template>
    <section class="svh" aria-labelledby="svh-title">
        <div class="svh-head">
            <div class="svh-heading">
                <h2 id="svh-title" class="svh-title">History</h2>
                <p v-if="note" class="svh-note">{{ note }}</p>
                <ThresholdLegend v-if="threshold && anyPoint" :threshold="threshold" class="svh-legend"></ThresholdLegend>
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
            <div v-for="index in skeletons" :key="index" class="svh-skeleton"></div>
        </div>
        <div v-else-if="charts.length === 0" class="svh-empty">
            <i class="fas fa-chart-line" aria-hidden="true"></i>
            <p>It runs on no server now.</p>
        </div>
        <div v-else-if="!anyPoint" class="svh-empty">
            <i class="fas fa-chart-line" aria-hidden="true"></i>
            <p><strong>{{ emptyTitle }}</strong> {{ emptyText }}</p>
        </div>
        <QueryHistoryGrid
            v-else
            :key="savedId"
            :history="history"
            :threshold="threshold"
            :states="states"
            :limit="SHOWN"
            :loading="loading"
            more-note="in the same order as the table"
        ></QueryHistoryGrid>
    </section>
</template>

<script>
import RangePicker from "@/components/ui/charts/RangePicker.vue"
import QueryHistoryGrid from "@/components/query/QueryHistoryGrid.vue"
import ThresholdLegend from "@/components/query/ThresholdLegend.vue"
import api from "@/api/queries"
import { DEFAULT_RANGE, RANGES } from "@/helpers/metrics"
import { hasPoints, historyCharts, pointNote, thresholdOf } from "@/helpers/queryHistory"
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
    components: { RangePicker, QueryHistoryGrid, ThresholdLegend },
    props: {
        savedId: { type: Number, required: true },
        severity: { type: String, default: "warning" },
        // The saved query's servers as its page shows them, worst first: `[{ server_id, state, meta, result }]`
        states: { type: Array, default: () => [] },
    },
    data() {
        return {
            SHOWN,
            range: rememberedRange(),
            history: null,
            loading: false,
            error: null,
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
        charts() {
            return historyCharts(this.history, this.states.map((entry) => entry.server_id))
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
    margin-top: 0.3rem;
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
}

.svh-skeleton {
    min-width: 0;
    height: 196px;
    border-radius: 6px;
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

.svh-alert {
    font-size: 0.875rem;
}
</style>
