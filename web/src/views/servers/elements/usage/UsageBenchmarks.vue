<template>
    <div class="benchmarks" :class="{ 'is-refreshing': loading && data }">
        <div class="bench-bar">
            <span v-if="data && data.date" class="bench-meta">
                {{ data.date }} (UTC) · read <timeSinceRefresh noicon :small="false" :timestamp="data.timestamp"></timeSinceRefresh>
            </span>
            <button
                type="button"
                class="btn btn-sm btn-outline-secondary bench-refresh"
                :disabled="loading"
                @click="load(true)"
            >
                <i :class="['fas', loading ? 'fa-circle-notch fa-spin' : 'fa-redo-alt']" aria-hidden="true"></i>
                {{ loading ? "Asking MISP…" : "Ask MISP again" }}
            </button>
        </div>

        <div v-if="loading && !data" class="bench-grid" aria-hidden="true">
            <div v-for="n in 3" :key="n" class="bench-card">
                <div class="skeleton skeleton-title"></div>
                <div v-for="row in 5" :key="row" class="skeleton skeleton-row"></div>
            </div>
        </div>
        <p v-else-if="requestError" class="bench-message is-error" role="alert">
            <i class="fas fa-exclamation-triangle" aria-hidden="true"></i> Could not load the benchmarks: {{ requestError }}
        </p>
        <template v-else-if="data">
            <p v-if="data.error" class="bench-message is-error" role="alert">
                <i class="fas fa-exclamation-triangle" aria-hidden="true"></i> {{ data.error }}
            </p>
            <p v-else-if="data.note" class="bench-message">{{ data.note }}</p>
            <div v-if="!data.error && !data.note" class="bench-grid">
                <section v-for="card in cards" :key="card.key" class="bench-card" :aria-label="card.title">
                    <h4 class="bench-title">{{ card.title }}</h4>
                    <table class="bench-table">
                        <thead>
                            <tr>
                                <th scope="col">Endpoint</th>
                                <th scope="col" class="num">Today</th>
                                <th scope="col" class="num">Per request</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="row in card.rows" :key="row.endpoint">
                                <th scope="row" class="bench-endpoint">
                                    <span class="endpoint-name" :title="row.endpoint">{{ row.endpoint }}</span>
                                    <span v-if="row.job" class="job-tag" title="A background job, not a web request">job</span>
                                    <span class="bench-meter" aria-hidden="true">
                                        <span class="bench-meter-fill" :style="{ width: `${row.share}%` }"></span>
                                    </span>
                                </th>
                                <td class="num">{{ row.total }}</td>
                                <td class="num">{{ row.average }}</td>
                            </tr>
                            <tr v-if="card.rows.length === 0">
                                <td colspan="3" class="bench-none">Nothing recorded today</td>
                            </tr>
                        </tbody>
                    </table>
                </section>
            </div>
        </template>
    </div>
</template>

<script>
import api from "@/api/metrics"
import { formatDuration, formatValue } from "@/helpers/metrics"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"

const FIELDS = [
    { key: "time", title: "Time spent" },
    { key: "sql_time", title: "SQL time" },
    { key: "memory", title: "Memory" },
]

export default {
    name: "UsageBenchmarks",
    components: { timeSinceRefresh },
    props: {
        serverId: { type: Number, required: true },
    },
    data() {
        return { data: null, loading: false, requestError: "" }
    },
    computed: {
        cards() {
            const fields = (this.data && this.data.fields) || {}
            return FIELDS.map(({ key, title }) => {
                const field = fields[key] || { unit: "s", top: [] }
                const format = (value) => (field.unit === "bytes" ? formatValue(value, "bytes") : formatDuration(value))
                const highest = Math.max(0, ...field.top.map((entry) => entry.total || 0))
                return {
                    key,
                    title,
                    rows: field.top.map((entry) => ({
                        endpoint: entry.endpoint,
                        job: entry.job,
                        total: format(entry.total),
                        average: format(entry.average),
                        share: highest > 0 ? Math.max(2, Math.round((entry.total / highest) * 100)) : 0,
                    })),
                }
            })
        },
    },
    mounted() {
        this.load(false)
    },
    methods: {
        load(refresh) {
            this.loading = true
            this.requestError = ""
            return api.benchmarks(this.serverId, refresh)
                .then((data) => {
                    this.data = data
                })
                .catch((error) => {
                    this.requestError = (error.response && error.response.data && error.response.data.message) || error.message
                })
                .finally(() => {
                    this.loading = false
                })
        },
    },
}
</script>

<style scoped>
.benchmarks {
    transition: opacity 0.15s;
}

.benchmarks.is-refreshing {
    opacity: 0.55;
}

.bench-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem 0.75rem;
    margin-bottom: 0.6rem;
}

.bench-meta {
    color: #6c757d;
    font-size: 0.8rem;
}

.bench-refresh {
    margin-left: auto;
    font-size: 0.78rem;
}

.bench-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 0.75rem;
}

.bench-card {
    min-width: 0;
    padding: 0.6rem 0.75rem;
    border: 1px solid #e4e7ec;
    border-radius: 6px;
    background: #fff;
}

.bench-title {
    margin: 0 0 0.35rem;
    font-size: 0.875rem;
    font-weight: 600;
    color: #212d40;
}

.bench-table {
    width: 100%;
    table-layout: fixed;
    border-collapse: collapse;
    font-size: 0.78rem;
}

.bench-table th,
.bench-table td {
    padding: 0.3rem 0;
    vertical-align: top;
}

.bench-table thead th {
    color: #6c757d;
    font-weight: 500;
    border-bottom: 1px solid #e4e7ec;
}

.bench-table thead th:first-child {
    width: 52%;
}

.bench-table tbody tr + tr th,
.bench-table tbody tr + tr td {
    border-top: 1px solid #f0f2f5;
}

.bench-table .num {
    padding-left: 0.5rem;
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}

.bench-table tbody td.num {
    color: #212d40;
}

.bench-endpoint {
    font-weight: 400;
    min-width: 0;
}

.endpoint-name {
    display: inline-block;
    max-width: calc(100% - 2.2rem);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    vertical-align: bottom;
    color: #212d40;
    font-family: SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.95em;
}

.job-tag {
    margin-left: 0.3rem;
    padding: 0 0.3rem;
    border-radius: 3px;
    background: #eef0f3;
    color: #52514e;
    font-size: 0.85em;
}

.bench-meter {
    display: block;
    height: 4px;
    margin-top: 0.2rem;
    border-radius: 2px;
    background: #eef3f9;
}

.bench-meter-fill {
    display: block;
    height: 100%;
    border-radius: 2px;
    background: #2a78d6;
}

.bench-none {
    color: #8a929c;
    text-align: center;
}

.bench-message {
    margin: 0;
    color: #6c757d;
    font-size: 0.85rem;
}

.bench-message.is-error {
    color: var(--health-critical-ink);
}

.skeleton {
    border-radius: 4px;
    background: linear-gradient(90deg, #f0f2f5 25%, #e6e9ee 37%, #f0f2f5 63%);
    background-size: 400% 100%;
    animation: shimmer 1.4s ease infinite;
}

.skeleton-title {
    width: 40%;
    height: 0.9rem;
    margin-bottom: 0.6rem;
}

.skeleton-row {
    height: 0.75rem;
    margin-bottom: 0.55rem;
}

@keyframes shimmer {
    0% { background-position: 100% 50%; }
    100% { background-position: 0 50%; }
}

@media (prefers-reduced-motion: reduce) {
    .skeleton {
        animation: none;
    }
}
</style>
