<template>
    <div class="servers-scroll">
        <table class="servers-table">
            <caption class="sr-only">Usage of each server of the fleet: latest sample, logins and changes {{ rangePhrase }}</caption>
            <colgroup>
                <col class="col-width-name">
                <col v-for="column in COLUMNS.slice(1)" :key="column.key">
            </colgroup>
            <thead>
                <tr>
                    <th
                        v-for="column in COLUMNS"
                        :key="column.key"
                        scope="col"
                        :class="['col', `col-${column.key}`, { 'is-numeric': column.key !== 'name' }]"
                        :aria-sort="sortKey === column.key ? (sortDesc ? 'descending' : 'ascending') : 'none'"
                    >
                        <button type="button" class="sort-button" :title="column.title" @click="sortOn(column.key)">
                            <span class="col-label">{{ column.label }}</span>
                            <span v-if="column.sub" class="col-sub">{{ column.sub }}</span>
                            <i :class="['fas', 'sort-icon', sortIcon(column.key)]" aria-hidden="true"></i>
                        </button>
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="row in sortedRows" :key="row.id">
                    <th scope="row" class="cell-name">
                        <router-link :to="serverLink(row.id)" class="server-name" :title="`Open the usage of ${row.name}`">{{ row.name }}</router-link>
                        <span :class="['server-status', `is-${statusOf(row).tone}`]" :title="statusOf(row).title">
                            <i v-if="statusOf(row).icon" :class="['fas', statusOf(row).icon]" aria-hidden="true"></i>
                            <template v-if="statusOf(row).showAge">
                                <timeSinceRefresh noicon :timestamp="row.lastTs"></timeSinceRefresh>
                            </template>
                            <template v-else>{{ statusOf(row).text }}</template>
                        </span>
                    </th>
                    <td class="is-numeric">
                        <span class="figure">{{ show(row.logins, "count") }}</span>
                        <span v-if="maxLogins > 0 && row.logins !== null" class="bar-track" aria-hidden="true">
                            <span class="bar-fill" :style="{ width: share(row.logins, maxLogins) }"></span>
                        </span>
                        <span v-if="row.failedLogins > 0" class="sub-figure">{{ show(row.failedLogins, "count") }} failed</span>
                    </td>
                    <td class="is-numeric">
                        <span class="figure">{{ show(row.apiRequests, "count") }}</span>
                    </td>
                    <td class="is-numeric">
                        <span class="figure">{{ show(row.load, "load") }}</span>
                        <span v-if="row.loadPeak !== null" class="sub-figure" :title="`Highest hourly or daily average ${rangePhrase}`">peak {{ show(row.loadPeak, "load") }}</span>
                    </td>
                    <td v-for="key in ['memory', 'disk']" :key="key" class="is-numeric">
                        <span class="figure">{{ show(row[key], "percent") }}</span>
                        <span v-if="row[key] !== null" class="bar-track" aria-hidden="true">
                            <span class="bar-fill" :style="{ width: share(row[key], 100) }"></span>
                        </span>
                    </td>
                    <td class="is-numeric">
                        <span class="figure">{{ show(row.dbSize, "bytes") }}</span>
                        <span v-if="row.dbChange !== null" class="sub-figure">{{ delta(row.dbChange, "bytes") }}</span>
                    </td>
                    <td class="is-numeric">
                        <span class="figure" :title="exact(row.events)">{{ show(row.events, "count") }}</span>
                        <span v-if="row.eventsChange !== null" class="sub-figure">{{ delta(row.eventsChange, "count") }}</span>
                    </td>
                    <td class="is-numeric">
                        <span :class="['figure', { 'is-zero': row.jobs === 0 }]">{{ show(row.jobs, "jobs") }}</span>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<script>
import { formatDelta, formatValue, sortRows } from "@/helpers/metrics"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"

const COLUMNS = [
    { key: "name", label: "Server", title: "Sort by name" },
    { key: "logins", label: "Logins", title: "Logins over the range, failed ones below" },
    { key: "apiRequests", label: "API requests", sub: "24 h", title: "API requests over the 24 hours before the latest sample, Fleet Commander's own left out" },
    { key: "load", label: "Load", sub: "1 min", title: "1-minute load average at the latest sample, highest average of the range below" },
    { key: "memory", label: "Memory", title: "Memory used" },
    { key: "disk", label: "Disk", title: "Disk used" },
    { key: "dbSize", label: "Database", title: "Size of MISP's database, change over the range below" },
    { key: "events", label: "Events", title: "Events, change over the range below" },
    { key: "jobs", label: "Jobs", sub: "waiting", title: "Jobs waiting in the worker queues" },
]

const STATUS = {
    failed: { tone: "warning", icon: "fa-exclamation-triangle", text: "Collection failed" },
    authkey: { tone: "warning", icon: "fa-key", text: "No API key" },
    waiting: { tone: "muted", icon: "fa-hourglass-half", text: "Waiting for a sample" },
}

// The servers of a fleet side by side: the figures that don't add up across servers (load, memory, disk) and each
// one's share of those that do. Sorted by name; a column header sorts on it, largest first
export default {
    name: "FleetUsageServers",
    components: { timeSinceRefresh },
    props: {
        // From `fleetServerRows`
        rows: { type: Array, required: true },
        rangePhrase: { type: String, default: "" },
    },
    data() {
        return {
            COLUMNS,
            sortKey: "name",
            sortDesc: false,
        }
    },
    computed: {
        sortedRows() {
            return sortRows(this.rows, this.sortKey, this.sortDesc)
        },
        maxLogins() {
            return Math.max(0, ...this.rows.map((row) => row.logins || 0))
        },
    },
    methods: {
        sortOn(key) {
            if (this.sortKey === key) {
                this.sortDesc = !this.sortDesc
            } else {
                this.sortKey = key
                this.sortDesc = key !== "name"
            }
        },
        sortIcon(key) {
            if (this.sortKey !== key) {
                return "fa-sort"
            }
            return this.sortDesc ? "fa-sort-down" : "fa-sort-up"
        },
        statusOf(row) {
            const { code, error } = row.status
            const status = STATUS[code]
            if (status) {
                // A failed collection says why, so that touch screens get the reason too
                return { ...status, showAge: false, text: error || status.text, title: error || status.text }
            }
            // Collected, or not collected at all (monitoring off, fleet not monitored: the tab's notice says so):
            // how old the latest sample is
            const partial = code === "partial"
            return {
                tone: partial ? "info" : "muted",
                icon: partial ? "fa-info-circle" : "",
                showAge: row.lastTs !== null,
                text: "No sample",
                title: partial ? `Some figures could not be read: ${error}` : "Latest sample",
            }
        },
        show(value, unit) {
            return formatValue(value, unit)
        },
        exact(value) {
            return value === null ? null : formatValue(value, "count", { exact: true })
        },
        delta(value, unit) {
            return formatDelta(value, unit)
        },
        share(value, whole) {
            return `${Math.max(0, Math.min(100, (value / whole) * 100))}%`
        },
        serverLink(serverId) {
            return { name: "servers.view", params: { server_id: serverId }, query: { tab: "usage" } }
        },
    },
}
</script>

<style scoped>
.servers-scroll {
    overflow-x: auto;
    border: 1px solid #e4e7ec;
    border-radius: 6px;
    background: #fff;
}

/* Fixed layout: the name column keeps its width and the figures share the rest evenly, so the spare width goes
   between the figures rather than between a name and its figures. Narrower screens scroll the table sideways */
.servers-table {
    width: 100%;
    min-width: 60rem;
    table-layout: fixed;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.8125rem;
    font-variant-numeric: tabular-nums;
}

.servers-table th,
.servers-table td {
    padding: 0.45rem 0.7rem;
    border-bottom: 1px solid var(--health-rule);
    vertical-align: top;
    white-space: nowrap;
}

.servers-table tbody tr:last-child th,
.servers-table tbody tr:last-child td {
    border-bottom: 0;
}

.servers-table tbody tr:hover th,
.servers-table tbody tr:hover td {
    background: #f8fafc;
}

thead th {
    padding: 0;
    background: #f8f9fb;
    color: #52514e;
    font-weight: 600;
    vertical-align: bottom;
}

.sort-button {
    display: inline-flex;
    align-items: baseline;
    gap: 0.3rem;
    width: 100%;
    padding: 0.45rem 0.7rem;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    text-align: left;
    white-space: nowrap;
}

.is-numeric .sort-button {
    justify-content: flex-end;
    text-align: right;
}

.sort-button:hover {
    color: #212d40;
}

.sort-button:focus-visible {
    outline: 2px solid rgba(41, 120, 160, 0.5);
    outline-offset: -2px;
}

.col-sub {
    color: #6c757d;
    font-weight: 400;
}

.sort-icon {
    font-size: 0.7rem;
    color: #b7bec7;
}

th[aria-sort="ascending"] .sort-icon,
th[aria-sort="descending"] .sort-icon {
    color: var(--var-color-lapislazuli);
}

th[aria-sort="ascending"],
th[aria-sort="descending"] {
    color: #212d40;
}

.col-width-name {
    width: 13rem;
}

.cell-name {
    position: sticky;
    left: 0;
    z-index: 1;
    background: #fff;
    font-weight: 400;
    text-align: left;
}

thead th.col-name {
    position: sticky;
    left: 0;
    z-index: 2;
}

.server-name {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    color: #212d40;
    font-weight: 600;
}

.server-status {
    display: block;
    margin-top: 0.1rem;
    overflow: hidden;
    text-overflow: ellipsis;
    color: #6c757d;
    font-size: 0.75rem;
}

.server-status i {
    margin-right: 0.2rem;
}

.server-status.is-warning {
    color: var(--health-warning-ink);
}

.server-status.is-info i {
    color: var(--health-info-ink);
}

td.is-numeric {
    text-align: right;
}

.figure {
    display: block;
    color: #212d40;
    font-weight: 500;
}

.figure.is-zero {
    color: #9aa1a7;
    font-weight: 400;
}

.sub-figure {
    display: block;
    margin-top: 0.1rem;
    color: #6c757d;
    font-size: 0.75rem;
}

.bar-track {
    display: block;
    width: 4.5rem;
    height: 4px;
    margin: 0.3rem 0 0 auto;
    border-radius: 2px;
    background: #e9edf2;
    overflow: hidden;
}

.bar-fill {
    display: block;
    height: 100%;
    border-radius: 2px;
    background: #2a78d6;
}
</style>
