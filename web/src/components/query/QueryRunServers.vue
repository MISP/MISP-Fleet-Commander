<template>
<div class="qs">
    <div class="qs-scroll">
        <table class="qs-table">
            <caption class="sr-only">Each server's answer</caption>
            <thead>
                <tr>
                    <th scope="col">Server</th>
                    <th scope="col">Outcome</th>
                    <th scope="col" :class="{ 'qs-num': kind === 'count' }">{{ kind === 'count' ? 'Count' : 'Answer' }}</th>
                    <th scope="col" class="qs-num">Time</th>
                    <th scope="col" class="qs-num" title="Requests sent to the server, the support check included">Requests</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="row in rows" :key="row.result.id" :class="{ 'qs-active': activeServer === row.result.server_id }">
                    <th scope="row" class="qs-server">{{ row.result.server_name }}</th>
                    <td>
                        <span :class="['qs-outcome', `job-tone-${row.outcome.tone}`]" :title="row.outcome.help || null">
                            <i :class="['fas', row.outcome.icon]" aria-hidden="true"></i>{{ row.outcome.label }}
                        </span>
                    </td>
                    <td v-if="kind === 'count' && row.count !== null" class="qs-num">
                        <span class="qs-count">{{ formatNumber(row.count) }}</span>
                        <span class="qs-bar" aria-hidden="true"><span :style="{ width: `${barWidth(row.count)}%` }"></span></span>
                    </td>
                    <td v-else class="qs-answer">
                        <b-button
                            v-if="row.rows > 0 && filterable"
                            variant="link"
                            size="sm"
                            class="qs-filter"
                            :aria-pressed="activeServer === row.result.server_id ? 'true' : 'false'"
                            :title="activeServer === row.result.server_id ? 'Show every server\'s rows' : 'Show only this server\'s rows'"
                            @click="$emit('filter', activeServer === row.result.server_id ? null : row.result.server_id)"
                        >{{ row.result.summary }}</b-button>
                        <span v-else :class="{ 'qs-detail': row.problem, 'qs-muted': row.skipped }" :title="row.title">{{ row.text }}</span>
                    </td>
                    <td class="qs-num qs-muted">{{ row.time }}</td>
                    <td class="qs-num qs-muted">{{ row.requests }}</td>
                </tr>
            </tbody>
            <tfoot v-if="kind === 'count' && counted > 0">
                <tr>
                    <th scope="row">Total</th>
                    <td class="qs-muted">{{ counted }} server{{ counted === 1 ? '' : 's' }}</td>
                    <td class="qs-num"><span class="qs-count">{{ formatNumber(total) }}</span><span class="qs-bar qs-bar-blank" aria-hidden="true"></span></td>
                    <td></td>
                    <td></td>
                </tr>
            </tfoot>
        </table>
    </div>
</div>
</template>

<script>
import { formatDuration, resultDuration } from "@/helpers/jobs"
import { resultOutcome } from "@/helpers/mispql"

const NUMBER = new Intl.NumberFormat()
const SKIPPED_TEXT = "Skipped: this MISP has no complex queries, so it was not searched"

// Each server's part in a run: its outcome, its answer in a few words, how long it took. For a COUNT, the counts
// side by side with a total
export default {
    name: "QueryRunServers",
    props: {
        results: { type: Array, default: () => [] },
        // select, count, describe or show_tables
        kind: { type: String, default: null },
        // The server whose rows are shown alone, if any
        activeServer: { type: Number, default: null },
        // Rows can be shown one server at a time
        filterable: { type: Boolean, default: false },
    },
    computed: {
        rows() {
            return this.results.map((result) => {
                const outcome = resultOutcome(result)
                const response = result.response || {}
                const count = response.outcome === "count" && typeof response.count === "number" ? response.count : null
                const duration = resultDuration(result)
                const skipped = outcome.name === "not_supported"
                return {
                    result,
                    outcome,
                    skipped,
                    problem: ["critical", "warning"].includes(outcome.tone),
                    count,
                    rows: response.outcome === "rows" ? response.rows || 0 : 0,
                    // A skip is no failure: say why in words, MISP's answer on hover
                    text: result.status === "pending" ? "" : (skipped ? SKIPPED_TEXT : (result.summary || "")),
                    title: skipped ? result.summary : null,
                    time: duration === null ? "" : formatDuration(duration),
                    requests: response.requests || "",
                }
            })
        },
        counted() {
            return this.rows.filter(row => row.count !== null).length
        },
        total() {
            return this.rows.reduce((sum, row) => sum + (row.count || 0), 0)
        },
        largest() {
            return this.rows.reduce((max, row) => Math.max(max, row.count || 0), 0)
        },
    },
    methods: {
        formatNumber(value) {
            return NUMBER.format(value)
        },
        barWidth(count) {
            if (!this.largest) {
                return 0
            }
            return Math.max(count > 0 ? 2 : 0, Math.round((count / this.largest) * 100))
        },
    },
}
</script>

<style scoped>
.qs-scroll {
    max-height: 26rem;
    overflow: auto;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    background: #fff;
}

.qs-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.86rem;
}

.qs-table th,
.qs-table td {
    padding: 0.45rem 0.75rem;
    border-bottom: 1px solid #eef0f3;
    vertical-align: middle;
}

.qs-table thead th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: #f6f7f9;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #5a6270;
    white-space: nowrap;
}

.qs-table tbody tr:last-child th,
.qs-table tbody tr:last-child td {
    border-bottom: 0;
}

.qs-table tfoot th,
.qs-table tfoot td {
    border-top: 1px solid var(--health-rule);
    border-bottom: 0;
    background: #fafbfc;
    font-weight: 700;
}

.qs-server {
    font-weight: 600;
    color: var(--var-color-yankeesblue);
    white-space: nowrap;
}

.qs-active {
    background: #f3f8fb;
}

.qs-outcome {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.12rem 0.5rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--job-ink);
    background: var(--job-tint);
    white-space: nowrap;
}

.qs-num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}

.qs-muted {
    color: #6b7380;
}

.qs-answer {
    color: #3c4452;
}

.qs-detail {
    color: #6b3a3a;
}

.qs-filter {
    padding: 0;
    font-size: inherit;
    vertical-align: baseline;
}

.qs-count {
    display: inline-block;
    min-width: 4rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
}

.qs-bar {
    display: inline-block;
    width: 8rem;
    height: 0.5rem;
    margin-left: 0.75rem;
    vertical-align: middle;
    background: #eef0f3;
    border-radius: 999px;
    overflow: hidden;
}

.qs-bar > span {
    display: block;
    height: 100%;
    background: var(--var-color-lapislazuli);
    border-radius: 999px;
}

.qs-bar-blank {
    background: transparent;
}
</style>
