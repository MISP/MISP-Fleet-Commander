<template>
    <div class="usage">
        <div class="usage-bar">
            <RangePicker :value="rangeKey" @input="setRange"></RangePicker>
            <span v-if="latestTs" class="usage-meta">
                Last sample <timeSinceRefresh noicon :small="false" :timestamp="latestTs"></timeSinceRefresh>
                <template v-if="intervalMinutes">· every {{ intervalMinutes }} min</template>
            </span>
            <span v-else-if="!hasHistory && snapshotTs" class="usage-meta">
                Last refresh <timeSinceRefresh noicon :small="false" :timestamp="snapshotTs"></timeSinceRefresh>
            </span>
            <span v-if="loading && data" class="usage-updating" role="status">
                <i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> Updating…
            </span>
        </div>

        <div v-if="notice" :class="['usage-notice', `is-${notice.level}`]" role="status">
            <i :class="['fas', 'fa-fw', notice.icon]" aria-hidden="true"></i>
            <div class="notice-text">
                <strong>{{ notice.title }}</strong>
                <span v-if="notice.text"> {{ notice.text }}</span>
                <button v-if="notice.action === 'settings'" type="button" class="btn btn-link notice-action" @click="openMonitoringSetting">
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
                <strong>Could not load the usage history.</strong> {{ requestError }}
                <button type="button" class="btn btn-link notice-action" @click="load()">Try again</button>
            </div>
        </div>

        <div v-if="!data && loading" class="usage-body" aria-hidden="true">
            <div v-for="section in 2" :key="`s${section}`" class="usage-section">
                <div class="skeleton skeleton-heading"></div>
                <div class="tile-grid">
                    <div v-for="tile in 4" :key="tile" class="skeleton skeleton-tile"></div>
                </div>
            </div>
            <div class="usage-section">
                <div class="skeleton skeleton-heading"></div>
                <div class="chart-grid">
                    <div v-for="chart in 2" :key="chart" class="skeleton skeleton-chart"></div>
                </div>
            </div>
        </div>

        <div v-else :class="['usage-body', { 'is-refreshing': loading && data }]">
            <section class="usage-section" aria-labelledby="usage-content-title">
                <header class="section-head">
                    <h3 id="usage-content-title" class="section-title">Content</h3>
                    <span class="section-note">{{ tileNote }}</span>
                </header>
                <div class="tile-grid">
                    <MetricTile v-for="tile in contentTiles" :key="tile.key" v-bind="tile"></MetricTile>
                </div>
                <p v-if="contentTiles.length === 0" class="section-empty">No statistics have been read from this server yet.</p>
            </section>

            <section v-if="communityTiles.length > 0" class="usage-section" aria-labelledby="usage-community-title">
                <header class="section-head">
                    <h3 id="usage-community-title" class="section-title">Community</h3>
                </header>
                <div class="tile-grid">
                    <MetricTile v-for="tile in communityTiles" :key="tile.key" v-bind="tile"></MetricTile>
                </div>
            </section>

            <template v-if="hasHistory">
                <section class="usage-section" aria-labelledby="usage-activity-title">
                    <header class="section-head">
                        <h3 id="usage-activity-title" class="section-title">Activity</h3>
                    </header>
                    <div class="chart-grid activity-grid">
                        <div class="chart-card activity-logins">
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
                        <div class="chart-card activity-heatmap">
                            <HourHeatmap
                                title="Logins by hour"
                                :subtitle="`last ${HEATMAP_DAYS} days, your time zone`"
                                :points="heatmapPoints"
                                :now="heatmapNow || data.to"
                                :days="HEATMAP_DAYS"
                            ></HourHeatmap>
                        </div>
                        <div class="chart-card activity-api">
                            <TimeSeriesChart
                                title="API requests"
                                :subtitle="`over the previous 24 hours, ${tierPhrase}`"
                                :series="apiSeries"
                                :from="data.from"
                                :to="data.to"
                                :interval="data.interval_s"
                                :height="140"
                            ></TimeSeriesChart>
                        </div>
                    </div>
                </section>

                <section class="usage-section" aria-labelledby="usage-system-title">
                    <header class="section-head">
                        <h3 id="usage-system-title" class="section-title">System</h3>
                        <span class="section-note">{{ bandNote }}</span>
                    </header>
                    <div class="chart-grid">
                        <div class="chart-card">
                            <TimeSeriesChart
                                title="Load average"
                                unit="load"
                                :series="loadSeries"
                                :from="data.from"
                                :to="data.to"
                                :interval="data.interval_s"
                            ></TimeSeriesChart>
                        </div>
                        <div class="chart-card">
                            <TimeSeriesChart
                                title="Memory and disk used"
                                unit="percent"
                                :y-max="100"
                                :series="memorySeries"
                                :from="data.from"
                                :to="data.to"
                                :interval="data.interval_s"
                            ></TimeSeriesChart>
                        </div>
                        <div class="chart-card">
                            <TimeSeriesChart
                                title="MISP database size"
                                unit="bytes"
                                :zero="false"
                                :series="databaseSeries"
                                :from="data.from"
                                :to="data.to"
                                :interval="data.interval_s"
                            ></TimeSeriesChart>
                        </div>
                    </div>
                </section>

                <section class="usage-section" aria-labelledby="usage-internals-title">
                    <header class="section-head">
                        <h3 id="usage-internals-title" class="section-title">MISP internals</h3>
                    </header>
                    <div class="chart-grid internals-grid">
                        <div class="chart-card">
                            <TimeSeriesChart
                                title="Redis memory"
                                unit="bytes"
                                :series="redisSeries"
                                :from="data.from"
                                :to="data.to"
                                :interval="data.interval_s"
                            ></TimeSeriesChart>
                        </div>
                        <div class="queues">
                            <div class="queues-head">
                                <span class="chart-title">Worker queues</span>
                                <span class="section-note">jobs waiting · maximum {{ periodPhrase }}</span>
                            </div>
                            <div class="tile-grid queue-grid">
                                <MetricTile v-for="tile in queueTiles" :key="tile.key" v-bind="tile"></MetricTile>
                            </div>
                        </div>
                    </div>
                </section>
            </template>

            <section v-else-if="data" class="usage-section">
                <p class="section-empty">
                    <i class="fas fa-chart-line" aria-hidden="true"></i>
                    Activity, system and queue charts appear here once samples have been collected.
                    The figures above come from the last refresh of the server.
                </p>
            </section>

            <section class="usage-section" aria-labelledby="usage-benchmarks-title">
                <header class="section-head">
                    <h3 id="usage-benchmarks-title" class="section-title">Endpoint benchmarks</h3>
                    <span class="section-note">today's most expensive requests, read live from MISP</span>
                    <button
                        type="button"
                        class="btn btn-sm btn-link section-toggle"
                        :aria-expanded="benchmarksOpen ? 'true' : 'false'"
                        aria-controls="usage-benchmarks"
                        @click="benchmarksOpen = !benchmarksOpen"
                    >
                        <i :class="['fas', benchmarksOpen ? 'fa-chevron-up' : 'fa-chevron-down']" aria-hidden="true"></i>
                        {{ benchmarksOpen ? "Hide" : "Show" }}
                    </button>
                </header>
                <div id="usage-benchmarks">
                    <UsageBenchmarks v-if="benchmarksOpen" :server-id="server_id"></UsageBenchmarks>
                </div>
            </section>
        </div>
    </div>
</template>

<script>
import { mapGetters, mapState } from "vuex"
import api from "@/api/metrics"
import { OPEN_SETTINGS_EVENT } from "@/views/settings/settingsModel"
import {
    changePhrase, collectionStatus, DEFAULT_RANGE, HOUR, loginBars, rangeOf, ratio, snapshotValues, stalledNotice,
} from "@/helpers/metrics"
import MetricTile from "@/components/ui/charts/MetricTile.vue"
import RangePicker from "@/components/ui/charts/RangePicker.vue"
import TimeSeriesChart from "@/components/ui/charts/TimeSeriesChart.vue"
import HourHeatmap from "@/components/ui/charts/HourHeatmap.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import UsageBenchmarks from "@/views/servers/elements/usage/UsageBenchmarks.vue"

const HEATMAP_DAYS = 14

const CONTENT = [
    { key: "events", label: "Events", icon: "fa-envelope" },
    { key: "attributes", label: "Attributes", icon: "fa-cube" },
    { key: "objects", label: "Objects", icon: "fa-cubes" },
    { key: "event_reports", label: "Event reports", icon: "fa-file-alt" },
    { key: "analyst_data", label: "Analyst data", icon: "fa-gavel" },
    { key: "correlations", label: "Correlations", icon: "fa-project-diagram" },
    { key: "proposals", label: "Proposals", icon: "fa-comment" },
]
const COMMUNITY = [
    { key: "users", label: "Users", icon: "fa-user" },
    { key: "orgs", label: "Organisations", icon: "fa-building" },
    { key: "contributing_orgs", label: "Contributing organisations", icon: "fa-handshake" },
    { key: "pending_registrations", label: "Pending registrations", icon: "fa-user-clock" },
]
const QUEUES = [
    { key: "queue_default", label: "Default" },
    { key: "queue_prio", label: "Priority" },
    { key: "queue_email", label: "Email" },
    { key: "queue_cache", label: "Cache" },
    { key: "queue_update", label: "Update" },
]

export default {
    name: "instanceUsage",
    components: {
        MetricTile, RangePicker, TimeSeriesChart, HourHeatmap, timeSinceRefresh, UsageBenchmarks,
    },
    props: {
        server_id: {
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
            benchmarksOpen: false,
            requestCount: 0,
        }
    },
    computed: {
        ...mapState({
            servers: (state) => state.servers.servers,
            serverUsage: (state) => state.servers.server_usage,
            lastRefresh: (state) => state.servers.last_refresh,
            fleets: (state) => state.fleets.all,
        }),
        ...mapGetters({
            isAdmin: "auth/isAdmin",
        }),
        range() {
            return rangeOf(this.rangeKey)
        },
        server() {
            return this.servers[this.server_id] || null
        },
        fleetMonitoredTimestamp() {
            const fleetId = this.server && this.server.fleet ? this.server.fleet.id : null
            const fleet = Object.values(this.fleets || {}).find((item) => item.id === fleetId)
            return fleet ? fleet.monitored_timestamp : null
        },
        hasHistory() {
            return Boolean(this.data && this.data.latest)
        },
        latestTs() {
            return this.hasHistory ? this.data.latest.ts : null
        },
        snapshotTs() {
            return this.lastRefresh[this.server_id] || null
        },
        intervalMinutes() {
            const interval = this.data && this.data.state && this.data.state.interval_s
            return interval ? Math.round(interval / 60) : null
        },
        values() {
            // The newest sample; without history, what the regular refresh read
            if (this.hasHistory) {
                return this.data.latest.values
            }
            const usage = this.serverUsage[this.server_id]
            return snapshotValues(usage && usage.stats)
        },
        periodPhrase() {
            // The samples may start after the range does (monitoring enabled recently)
            const events = this.hasHistory ? this.data.series.events || [] : []
            return changePhrase(this.range, this.data ? this.data.from : 0, events.length > 0 ? events[0][0] : null)
        },
        tileNote() {
            return this.hasHistory ? `change ${this.periodPhrase}` : "from the last refresh, without history"
        },
        tierPhrase() {
            const tier = this.data && this.data.tier
            return { raw: "every sample", hour: "hourly average", day: "daily average" }[tier] || ""
        },
        bandNote() {
            const tier = this.data && this.data.tier
            if (tier === "hour") return "hourly averages, shaded up to each hour's maximum"
            if (tier === "day") return "daily averages, shaded up to each day's maximum"
            return "every sample"
        },
        contentTiles() {
            const values = this.values
            const notes = {
                attributes: this.perEvent(values.attributes, values.events),
                objects: this.perEvent(values.objects, values.events),
            }
            return CONTENT.filter((tile) => this.isKnown(tile.key)).map((tile) => this.tile(tile, notes[tile.key]))
        },
        communityTiles() {
            const values = this.values
            const share = (part, whole) => {
                const value = ratio(part, whole, 3)
                return value === null ? "" : `${Math.round(value * 100)}%`
            }
            const notes = {
                users: values.users_pgp !== undefined && values.users ? `${share(values.users_pgp, values.users)} with a PGP key` : "",
                orgs: values.local_orgs !== undefined ? `${values.local_orgs.toLocaleString("en-US")} local` : "",
                contributing_orgs: values.orgs ? `${share(values.contributing_orgs, values.orgs)} of the organisations` : "",
            }
            return COMMUNITY.filter((tile) => this.isKnown(tile.key)).map((tile) => this.tile(tile, notes[tile.key]))
        },
        queueTiles() {
            return QUEUES.filter((tile) => this.isKnown(tile.key)).map((tile) => ({
                ...this.tile(tile),
                icon: "",
                unit: "jobs",
                kind: "gauge",
                peaks: this.peaksOf(tile.key),
            }))
        },
        apiSeries() {
            return this.lineSeries([{ key: "api_requests_24h", label: "Requests" }])
        },
        loadSeries() {
            // The 5 and 15 minute loads smooth the 1 minute one: a band each would pile up into a grey mass
            return this.lineSeries([
                { key: "load_1", label: "1 min" },
                { key: "load_5", label: "5 min", band: false },
                { key: "load_15", label: "15 min", band: false },
            ])
        },
        memorySeries() {
            return this.lineSeries([{ key: "memory_used_pct", label: "Memory" }, { key: "disk_used_pct", label: "Disk" }])
        },
        databaseSeries() {
            return this.lineSeries([{ key: "db_size_bytes", label: "Size" }])
        },
        redisSeries() {
            return this.lineSeries([
                { key: "redis_memory_bytes", label: "Used" },
                { key: "redis_memory_peak_bytes", label: "Peak since Redis started", band: false },
            ])
        },
        loginBarsData() {
            return loginBars(this.data ? this.data.series : {}, this.rangeKey, this.data ? this.data.interval_s : HOUR)
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
        notice() {
            if (!this.data) {
                return null
            }
            const status = collectionStatus(this.data.state)
            const interval = this.intervalMinutes
            const past = this.hasHistory ? " The charts show what was collected before." : ""
            switch (status.code) {
            case "off":
                return {
                    level: "muted",
                    icon: "fa-power-off",
                    title: "Monitoring is off.",
                    text: (this.isAdmin
                        ? "Enable it in the settings (Scheduler tab) to keep a history of this server's usage."
                        : "An administrator can enable it in the settings to keep a history of this server's usage.") + past,
                    action: this.isAdmin ? "settings" : null,
                }
            case "fleet":
                return {
                    level: "muted",
                    icon: "fa-eye-slash",
                    title: "This server's fleet is not monitored.",
                    text: `Edit the fleet and tick "Monitor" to collect the usage of its servers.${past}`,
                    action: "fleet",
                }
            case "authkey":
                return {
                    level: "warning",
                    icon: "fa-key",
                    title: "This server has no API key,",
                    text: "so its usage cannot be read from MISP.",
                }
            case "stalled":
                return stalledNotice(status.lastRun, { now: this.data.to, isAdmin: this.isAdmin, past })
            case "waiting":
                return {
                    level: "info",
                    icon: "fa-hourglass-half",
                    title: "Waiting for the first sample.",
                    text: `It is collected within a minute${interval ? `, then every ${interval} minutes` : ""}.`,
                }
            case "failed":
                return {
                    level: "warning",
                    icon: "fa-exclamation-triangle",
                    title: "The last collection failed:",
                    text: status.error,
                }
            case "partial":
                return {
                    level: "muted",
                    icon: "fa-info-circle",
                    title: "Some figures could not be read at the last collection:",
                    text: status.error,
                }
            default:
                return null
            }
        },
    },
    watch: {
        server_id() {
            this.data = null
            this.reload()
        },
        fleetMonitoredTimestamp(current, previous) {
            // A collection tick went through the server's fleet: show its sample, without dimming the tab
            if (previous && current && current !== previous) {
                this.reload({ quiet: true })
            }
        },
    },
    mounted() {
        this.reload()
    },
    methods: {
        openMonitoringSetting() {
            this.$root.$emit(OPEN_SETTINGS_EVENT, { focus: "monitoring_enabled" })
        },
        reload(options = {}) {
            this.load(options)
            this.loadHeatmap()
        },
        load({ quiet = false } = {}) {
            const request = this.requestCount + 1
            this.requestCount = request
            this.loading = !quiet || this.loading
            this.requestError = ""
            return api.series(this.server_id, { range: this.rangeKey })
                .then((data) => {
                    if (request === this.requestCount) {
                        this.data = data
                    }
                })
                .catch((error) => {
                    if (request === this.requestCount) {
                        // The client rejects with the server's message alone when it gave one
                        this.requestError = typeof error === "string" ? error : (error && error.message) || "Unknown error"
                    }
                })
                .finally(() => {
                    if (request === this.requestCount) {
                        this.loading = false
                    }
                })
        },
        loadHeatmap() {
            // Last 14 days of hourly logins, whatever the range (the 30-day hourly series, cut by the heatmap)
            return api.series(this.server_id, { range: "30d", tier: "hour", metrics: ["logins"] })
                .then((data) => {
                    this.heatmapPoints = data.series.logins || []
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
        isKnown(key) {
            const value = this.values[key]
            return value !== undefined && value !== null
        },
        series(key) {
            return this.data && this.data.series ? this.data.series[key] || [] : null
        },
        tile({ key, label, icon }, note = "") {
            return {
                key,
                label,
                icon,
                value: this.values[key],
                points: this.hasHistory ? this.series(key) : null,
                rangePhrase: this.periodPhrase,
                note,
            }
        },
        perEvent(count, events) {
            const value = ratio(count, events)
            return value === null ? "" : `${value.toLocaleString("en-US")} per event`
        },
        lineSeries(items) {
            return items.map(({ key, label, band }) => ({
                key,
                label,
                band,
                points: this.series(key) || [],
                peaks: this.peaksOf(key),
            }))
        },
        peaksOf(key) {
            return (this.data && this.data.peaks && this.data.peaks[key]) || []
        },
    },
}
</script>

<style scoped src="@/components/ui/charts/usageLayout.css"></style>

<style scoped>
@media (min-width: 1100px) {
    .internals-grid {
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }
}

.queues {
    min-width: 0;
}

.queues-head {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.15rem 0.5rem;
    margin: 0.6rem 0 0.45rem;
}

.queue-grid {
    grid-template-columns: repeat(auto-fill, minmax(118px, 1fr));
}

@media (max-width: 480px) {
    .queue-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
</style>
