<template>
    <div class="usage fleet-usage">
        <div class="usage-bar">
            <RangePicker :value="rangeKey" @input="setRange"></RangePicker>
            <span v-if="data && collection.total > 0 && monitored" :class="['usage-meta', 'reporting', { 'is-short': collection.reporting < collection.total }]">
                <i class="fas fa-server" aria-hidden="true"></i>
                {{ reportingText }}
            </span>
            <span v-if="data && data.latest_ts" class="usage-meta">
                Last sample <timeSinceRefresh noicon :small="false" :timestamp="data.latest_ts"></timeSinceRefresh>
                <template v-if="intervalMinutes">· every {{ intervalMinutes }} min</template>
            </span>
            <span v-if="loading && data" class="usage-updating" role="status">
                <i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> Updating…
            </span>
        </div>

        <div v-for="notice in notices" :key="notice.key" :class="['usage-notice', `is-${notice.level}`]" role="status">
            <i :class="['fas', 'fa-fw', notice.icon]" aria-hidden="true"></i>
            <div class="notice-text">
                <strong>{{ notice.title }}</strong>
                <template v-if="notice.servers">
                    {{ " " }}<template v-for="(server, index) in notice.servers">
                        <router-link
                            :key="server.id"
                            :to="serverLink(server.id)"
                            class="notice-server"
                        >{{ server.name }}</router-link>{{ index < notice.servers.length - 1 ? ", " : "" }}</template>
                    <template v-if="notice.more"> and {{ notice.more }} more</template>{{ notice.reason ? ` (${notice.reason}).` : "." }}
                </template>
                <span v-if="notice.text"> {{ notice.text }}</span>
                <button v-if="notice.action === 'settings'" type="button" class="btn btn-link notice-action" @click="$bvModal.show('modal-settings')">
                    Open the settings
                </button>
                <router-link v-else-if="notice.action === 'fleet'" :to="{ name: 'home' }" class="notice-action">
                    Go to the fleets
                </router-link>
            </div>
        </div>

        <div v-if="requestError" class="usage-notice is-critical" role="alert">
            <i class="fas fa-fw fa-exclamation-triangle" aria-hidden="true"></i>
            <div class="notice-text">
                <strong>Could not load the fleet's usage.</strong> {{ requestError }}
                <button type="button" class="btn btn-link notice-action" @click="load()">Try again</button>
            </div>
        </div>

        <div v-if="!data && loading" class="usage-body" aria-hidden="true">
            <div class="usage-section">
                <div class="skeleton skeleton-heading"></div>
                <div class="tile-grid">
                    <div v-for="tile in 6" :key="tile" class="skeleton skeleton-tile"></div>
                </div>
            </div>
            <div class="usage-section">
                <div class="skeleton skeleton-heading"></div>
                <div class="chart-grid">
                    <div v-for="chart in 2" :key="chart" class="skeleton skeleton-chart"></div>
                </div>
            </div>
        </div>

        <div v-else-if="data && collection.total > 0" :class="['usage-body', { 'is-refreshing': loading }]">
            <template v-if="hasHistory">
                <section class="usage-section" aria-labelledby="fleet-usage-totals-title">
                    <header class="section-head">
                        <h3 id="fleet-usage-totals-title" class="section-title">Fleet totals</h3>
                        <span class="section-note">summed over the servers · change {{ periodPhrase }}</span>
                    </header>
                    <div class="tile-grid">
                        <MetricTile v-for="tile in tiles" :key="tile.key" v-bind="tile"></MetricTile>
                    </div>
                    <p class="section-footnote">
                        <i class="fas fa-info-circle" aria-hidden="true"></i>
                        Content synchronised between servers counts once on each server that holds it.
                    </p>
                </section>

                <section class="usage-section" aria-labelledby="fleet-usage-activity-title">
                    <header class="section-head">
                        <h3 id="fleet-usage-activity-title" class="section-title">Activity</h3>
                        <span class="section-note">all servers together</span>
                    </header>
                    <div class="chart-grid activity-grid">
                        <div class="chart-card">
                            <TimeSeriesChart
                                title="Logins"
                                :subtitle="loginBarsData.size === HOUR ? 'per hour' : 'per day (UTC)'"
                                mode="bars"
                                :series="loginSeries"
                                :from="data.from"
                                :to="data.to"
                                :interval="loginBarsData.size"
                                :partial-since="loginPartialSince"
                                :height="228"
                            ></TimeSeriesChart>
                        </div>
                        <div class="chart-card">
                            <HourHeatmap
                                title="Logins by hour"
                                :subtitle="`last ${HEATMAP_DAYS} days, your time zone`"
                                :points="heatmapPoints"
                                :now="heatmapNow || data.to"
                                :days="HEATMAP_DAYS"
                            ></HourHeatmap>
                        </div>
                    </div>
                    <div class="chart-grid fleet-pair">
                        <div class="chart-card">
                            <TimeSeriesChart
                                title="API requests"
                                :subtitle="`over the previous 24 hours, ${tierPhrase}`"
                                :series="lineSeries('api_requests_24h', 'Requests')"
                                :from="data.from"
                                :to="data.to"
                                :interval="data.interval_s"
                                :partial-since="data.partial_since"
                                :height="150"
                            ></TimeSeriesChart>
                        </div>
                        <div class="chart-card">
                            <TimeSeriesChart
                                title="MISP database size"
                                :subtitle="`all databases, ${tierPhrase}`"
                                unit="bytes"
                                :zero="false"
                                :series="lineSeries('db_size_bytes', 'Size')"
                                :from="data.from"
                                :to="data.to"
                                :interval="data.interval_s"
                                :partial-since="data.partial_since"
                                :height="150"
                            ></TimeSeriesChart>
                        </div>
                    </div>
                </section>
            </template>

            <section v-else class="usage-section">
                <p class="section-empty">
                    <i class="fas fa-chart-line" aria-hidden="true"></i>
                    Fleet totals and charts appear here once samples have been collected from its servers.
                </p>
            </section>

            <section class="usage-section" aria-labelledby="fleet-usage-servers-title">
                <header class="section-head">
                    <h3 id="fleet-usage-servers-title" class="section-title">Servers</h3>
                    <span class="section-note">latest sample of each server · logins and changes {{ rangePhrase }}</span>
                </header>
                <FleetUsageServers :rows="serverRows" :range-phrase="rangePhrase"></FleetUsageServers>
            </section>
        </div>
    </div>
</template>

<script>
import { mapGetters, mapState } from "vuex"
import api from "@/api/metrics"
import {
    changePhrase, DEFAULT_RANGE, fleetCollection, fleetServerRows, HOUR, lastValue, loginBars, QUEUE_KEYS, rangeOf,
    ratio, sumSeries,
} from "@/helpers/metrics"
import MetricTile from "@/components/ui/charts/MetricTile.vue"
import RangePicker from "@/components/ui/charts/RangePicker.vue"
import TimeSeriesChart from "@/components/ui/charts/TimeSeriesChart.vue"
import HourHeatmap from "@/components/ui/charts/HourHeatmap.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import FleetUsageServers from "@/components/usage/FleetUsageServers.vue"

const HEATMAP_DAYS = 14
// Servers named in a notice before "and N more"
const NAMED_SERVERS = 3

// What the tab draws: fleet sums, and the servers table's figures (load, memory and disk are not summed)
const TAB_METRICS = [
    "events", "attributes", "users", "users_pgp", "db_size_bytes", "api_requests_24h", ...QUEUE_KEYS, "logins",
    "failed_logins", "load_1", "memory_used_pct", "disk_used_pct",
]

const TILES = [
    { key: "events", label: "Events", icon: "fa-envelope" },
    { key: "attributes", label: "Attributes", icon: "fa-cube" },
    { key: "users", label: "Users", icon: "fa-user" },
    // A database grows: its change says more than its maximum
    { key: "db_size_bytes", label: "Database size", icon: "fa-database", unit: "bytes" },
    { key: "api_requests_24h", label: "API requests (24 h)", icon: "fa-exchange-alt", kind: "gauge" },
    { key: "jobs", label: "Jobs waiting", icon: "fa-tasks", unit: "jobs", kind: "gauge" },
]

export default {
    name: "FleetUsageTab",
    components: {
        MetricTile, RangePicker, TimeSeriesChart, HourHeatmap, timeSinceRefresh, FleetUsageServers,
    },
    props: {
        fleetId: {
            required: true,
            type: Number,
        },
    },
    data() {
        return {
            HOUR,
            HEATMAP_DAYS,
            rangeKey: DEFAULT_RANGE,
            data: null,
            loading: false,
            requestError: "",
            heatmapPoints: [],
            heatmapNow: null,
            requestCount: 0,
        }
    },
    computed: {
        ...mapState({
            fleets: (state) => state.fleets.all,
        }),
        ...mapGetters({
            isAdmin: "auth/isAdmin",
        }),
        range() {
            return rangeOf(this.rangeKey)
        },
        fleetMonitoredTimestamp() {
            const fleet = Object.values(this.fleets || {}).find((item) => item.id === this.fleetId)
            return fleet ? fleet.monitored_timestamp : null
        },
        totals() {
            return (this.data && this.data.totals) || {}
        },
        monitored() {
            return Boolean(this.data && this.data.state.enabled && this.data.state.fleet_monitored)
        },
        hasHistory() {
            return Object.values(this.totals).some((points) => points && points.length > 0)
        },
        collection() {
            return fleetCollection(this.data ? this.data.servers : [])
        },
        reportingText() {
            const { reporting, total } = this.collection
            if (reporting === total) {
                return total === 1 ? "The server is reporting" : `All ${total} servers reporting`
            }
            return `${reporting} of ${total} servers reporting`
        },
        intervalMinutes() {
            const interval = this.data && this.data.state && this.data.state.interval_s
            return interval ? Math.round(interval / 60) : null
        },
        rangePhrase() {
            return `over ${this.range.phrase}`
        },
        periodPhrase() {
            // The samples may start after the range does (monitoring enabled recently)
            const events = this.totals.events || []
            return changePhrase(this.range, this.data ? this.data.from : 0, events.length > 0 ? events[0][0] : null)
        },
        tierPhrase() {
            return { hour: "hourly average", day: "daily average" }[this.data && this.data.tier] || ""
        },
        jobsSeries() {
            return sumSeries(QUEUE_KEYS.map((key) => this.totals[key]))
        },
        tiles() {
            const pointsOf = (key) => (key === "jobs" ? this.jobsSeries : this.totals[key] || [])
            const latest = (key) => lastValue(pointsOf(key))
            const pgp = ratio(latest("users_pgp"), latest("users"), 3)
            const notes = {
                attributes: this.perEvent(latest("attributes"), latest("events")),
                users: pgp === null ? "" : `${Math.round(pgp * 100)}% with a PGP key`,
                jobs: "in all queues",
            }
            return TILES.filter((tile) => latest(tile.key) !== null).map((tile) => ({
                key: tile.key,
                label: tile.label,
                icon: tile.icon,
                unit: tile.unit || "count",
                kind: tile.kind || "total",
                value: latest(tile.key),
                points: pointsOf(tile.key),
                rangePhrase: this.periodPhrase,
                note: notes[tile.key] || "",
            }))
        },
        loginBarsData() {
            return loginBars(this.totals, this.rangeKey, this.data ? this.data.interval_s : HOUR)
        },
        loginSeries() {
            return [
                { key: "logins", label: "Logins", points: this.loginBarsData.logins },
                { key: "failed_logins", label: "Failed logins", points: this.loginBarsData.failed_logins },
            ]
        },
        loginPartialSince() {
            if (!this.data) {
                return null
            }
            const size = this.loginBarsData.size
            return this.data.to - (this.data.to % size)
        },
        serverRows() {
            return fleetServerRows(this.data ? this.data.servers : [])
        },
        notices() {
            if (!this.data) {
                return []
            }
            const { state } = this.data
            const past = this.hasHistory ? " The charts show what was collected before." : ""
            if (!state.enabled) {
                return [{
                    key: "off",
                    level: "muted",
                    icon: "fa-power-off",
                    title: "Monitoring is off.",
                    text: (this.isAdmin
                        ? "Enable it in the settings (Scheduler tab) to keep a history of the fleet's usage."
                        : "An administrator can enable it in the settings to keep a history of the fleet's usage.") + past,
                    action: this.isAdmin ? "settings" : null,
                }]
            }
            if (!state.fleet_monitored) {
                return [{
                    key: "fleet",
                    level: "muted",
                    icon: "fa-eye-slash",
                    title: "This fleet is not monitored.",
                    text: `Edit the fleet and tick "Monitor" to collect the usage of its servers.${past}`,
                    action: "fleet",
                }]
            }
            if (state.servers === 0) {
                return [{
                    key: "empty",
                    level: "muted",
                    icon: "fa-server",
                    title: "This fleet has no servers yet.",
                    text: "Their usage shows here once they are added and collected.",
                }]
            }
            const { failed, authkey, waiting, total } = this.collection
            const notices = []
            if (failed.length > 0) {
                notices.push(this.serversNotice("failed", "fa-exclamation-triangle", failed, "The last collection failed on"))
            }
            if (authkey.length > 0) {
                notices.push(this.serversNotice("authkey", "fa-key", authkey, "No API key on"))
            }
            if (waiting.length > 0 && waiting.length === total) {
                notices.push({
                    key: "waiting",
                    level: "info",
                    icon: "fa-hourglass-half",
                    title: "Waiting for the first samples.",
                    text: `They are collected within a minute${this.intervalMinutes ? `, then every ${this.intervalMinutes} minutes` : ""}.`,
                })
            }
            return notices
        },
    },
    watch: {
        fleetId() {
            this.data = null
            this.reload()
        },
        fleetMonitoredTimestamp(current, previous) {
            // A collection tick went through the fleet: show its samples, without dimming the tab
            if (previous && current && current !== previous) {
                this.reload({ quiet: true })
            }
        },
    },
    mounted() {
        this.reload()
    },
    methods: {
        reload(options = {}) {
            this.load(options)
            this.loadHeatmap()
        },
        load({ quiet = false } = {}) {
            const request = this.requestCount + 1
            this.requestCount = request
            this.loading = !quiet || this.loading
            this.requestError = ""
            return api.fleetSeries(this.fleetId, { range: this.rangeKey, metrics: TAB_METRICS })
                .then((data) => {
                    if (request === this.requestCount) {
                        this.data = data
                    }
                })
                .catch((error) => {
                    if (request === this.requestCount) {
                        this.requestError = (error.response && error.response.data && error.response.data.message) || error.message
                    }
                })
                .finally(() => {
                    if (request === this.requestCount) {
                        this.loading = false
                    }
                })
        },
        loadHeatmap() {
            // Last 14 days of the fleet's hourly logins, whatever the range (the 30-day hourly sums, cut by the heatmap)
            return api.fleetSeries(this.fleetId, { range: "30d", metrics: ["logins"] })
                .then((data) => {
                    this.heatmapPoints = data.totals.logins || []
                    this.heatmapNow = data.to
                })
                .catch(() => {
                    this.heatmapPoints = []
                })
        },
        setRange(key) {
            if (key !== this.rangeKey) {
                this.rangeKey = key
                this.load()
            }
        },
        lineSeries(key, label) {
            return [{ key, label, points: this.totals[key] || [], band: false }]
        },
        perEvent(count, events) {
            const value = ratio(count, events)
            return value === null ? "" : `${value.toLocaleString("en-US")} per event`
        },
        serverLink(serverId) {
            return { name: "servers.view", params: { server_id: serverId }, query: { tab: "usage" } }
        },
        serversNotice(key, icon, servers, title) {
            // One server: its reason inline. Several: their rows in the table below give theirs
            const reason = servers.length === 1 ? servers[0].error : ""
            return {
                key,
                level: "warning",
                icon,
                title,
                servers: servers.slice(0, NAMED_SERVERS),
                more: Math.max(0, servers.length - NAMED_SERVERS),
                reason,
                text: {
                    failed: servers.length > 1 ? "Their rows below give the reason." : "",
                    authkey: `${servers.length > 1 ? "Their" : "Its"} usage cannot be read without one.`,
                }[key],
            }
        },
    },
}
</script>

<style scoped src="@/components/ui/charts/usageLayout.css"></style>

<style scoped>
.fleet-usage {
    padding-left: 0;
    padding-right: 0;
}

.reporting .fa-server {
    margin-right: 0.2rem;
    color: #9aa1a7;
}

.reporting.is-short {
    color: var(--health-warning-ink);
    font-weight: 600;
}

.reporting.is-short .fa-server {
    color: var(--health-warning);
}

.notice-server {
    font-weight: 600;
}

.section-footnote {
    margin: 0.5rem 0 0;
    color: #6c757d;
    font-size: 0.78rem;
}

.section-footnote i {
    margin-right: 0.25rem;
    color: #9aa1a7;
}

.fleet-pair {
    margin-top: 0.75rem;
}

@media (min-width: 1100px) {
    .fleet-pair {
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }
}
</style>
