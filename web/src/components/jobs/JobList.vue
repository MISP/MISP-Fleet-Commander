<template>
    <div class="job-list">
        <div class="job-filters" role="search" aria-label="Filter jobs">
            <div class="job-filter-row">
                <div class="job-status-filter" role="group" aria-label="Status">
                    <button
                        v-for="option in statusFilters"
                        :key="option.value"
                        type="button"
                        :class="['job-status-option', { active: filters.status === option.value }]"
                        :aria-pressed="filters.status === option.value ? 'true' : 'false'"
                        @click="setFilter('status', option.value)"
                    >{{ option.label }}</button>
                </div>
                <div v-if="showScope" class="job-scope" role="group" aria-label="Whose jobs">
                    <button
                        v-for="option in scopes"
                        :key="option.value"
                        type="button"
                        :class="['job-status-option', { active: filters.scope === option.value }]"
                        :aria-pressed="filters.scope === option.value ? 'true' : 'false'"
                        :title="option.help"
                        @click="setFilter('scope', option.value)"
                    >{{ option.label }}</button>
                </div>
            </div>
            <div class="job-filter-row">
                <b-input-group size="sm" class="job-search">
                    <b-input-group-prepend is-text>
                        <i class="fas fa-search" aria-hidden="true"></i>
                    </b-input-group-prepend>
                    <b-form-input
                        v-model="search"
                        type="search"
                        :placeholder="searchPlaceholder"
                        aria-label="Search jobs"
                    ></b-form-input>
                </b-input-group>
                <b-form-select
                    v-model="filters.kind"
                    :options="kindOptions"
                    size="sm"
                    class="job-select"
                    aria-label="Kind"
                ></b-form-select>
                <b-form-select
                    v-if="showFleetFilter"
                    v-model="filters.fleet_id"
                    :options="fleetOptions"
                    size="sm"
                    class="job-select"
                    aria-label="Fleet"
                ></b-form-select>
                <b-form-select
                    v-model="filters.since"
                    :options="periods"
                    size="sm"
                    class="job-select"
                    aria-label="Period"
                ></b-form-select>
                <b-button
                    v-if="filtered"
                    size="sm"
                    variant="link"
                    class="job-clear"
                    @click="clearFilters"
                >Clear filters</b-button>
                <span class="job-list-count" aria-live="polite">
                    <b-spinner v-if="refreshing" small class="mr-1" label="Updating"></b-spinner>
                    <template v-if="loaded">{{ countLabel }}</template>
                </span>
            </div>
        </div>

        <button
            v-if="newJobs"
            type="button"
            class="job-new-pill"
            @click="showLatest"
        >
            <i class="fas fa-arrow-up mr-1" aria-hidden="true"></i>New jobs: show the latest
        </button>

        <b-alert :show="!!error" variant="danger" class="mb-2">
            <strong>Could not load the jobs.</strong> {{ error }}
            <b-button size="sm" variant="outline-danger" class="ml-2" @click="fetch()">Try again</b-button>
        </b-alert>

        <div :class="['job-table-wrap', { 'is-refreshing': refreshing }]">
            <table class="job-table">
                <colgroup>
                    <col class="col-status">
                    <col>
                    <col class="col-servers">
                    <col class="col-when">
                    <col class="col-duration">
                </colgroup>
                <thead>
                    <tr>
                        <th scope="col">Status</th>
                        <th scope="col">Job</th>
                        <th scope="col">{{ serverId ? 'This server' : 'Servers' }}</th>
                        <th scope="col">Started</th>
                        <th scope="col" class="text-right">Duration</th>
                    </tr>
                </thead>
                <tbody v-if="!loaded && !error">
                    <tr v-for="n in 4" :key="`skeleton-${n}`" class="job-skeleton" aria-hidden="true">
                        <td><span class="bone bone-badge"></span></td>
                        <td><span class="bone bone-title"></span><span class="bone bone-meta"></span></td>
                        <td><span class="bone bone-bar"></span></td>
                        <td><span class="bone bone-short"></span></td>
                        <td><span class="bone bone-short ml-auto"></span></td>
                    </tr>
                </tbody>
                <tbody v-else-if="rows.length > 0">
                    <tr
                        v-for="row in rows"
                        :key="row.id"
                        :class="['job-row', `job-row-${row.status}`]"
                        @click="openRow($event, row)"
                    >
                        <td class="cell-status">
                            <JobStatusBadge :status="row.status" small></JobStatusBadge>
                        </td>
                        <td class="cell-job">
                            <router-link :to="{ name: 'jobs.view', params: { job_id: row.id } }" class="job-link">
                                {{ row.title || kindLabel(row.kind) }}
                            </router-link>
                            <div class="job-row-meta">
                                <span>{{ kindLabel(row.kind) }}</span>
                                <template v-if="showFleet && row.fleet_name">
                                    <span class="dot" aria-hidden="true">·</span>
                                    <span :title="row.fleet_id ? '' : 'This fleet was deleted'" :class="{ 'is-gone': !row.fleet_id }">
                                        <i class="fas fa-server fa-xs mr-1" aria-hidden="true"></i>{{ row.fleet_name }}
                                    </span>
                                </template>
                                <template v-if="showUser(row)">
                                    <span class="dot" aria-hidden="true">·</span>
                                    <span :class="{ 'is-gone': !row.user_id }" :title="row.user_id ? '' : 'This user was deleted'">
                                        <i class="fas fa-user fa-xs mr-1" aria-hidden="true"></i>{{ row.user_email || 'Unknown user' }}<template v-if="!row.user_id"> (deleted)</template>
                                    </span>
                                </template>
                            </div>
                        </td>
                        <td class="cell-servers">
                            <template v-if="serverId">
                                <span v-if="row.server_result" class="server-result" :title="row.server_result.summary || ''">
                                    <JobStatusBadge :status="row.server_result.status" of="result" small></JobStatusBadge>
                                    <span v-if="row.server_result.summary" class="server-result-summary">{{ row.server_result.summary }}</span>
                                </span>
                                <span v-if="row.total > 1" class="job-tally-small">{{ tallyLabel(row) }} of {{ row.total }}</span>
                            </template>
                            <template v-else>
                                <span
                                    class="job-mini-bar"
                                    role="img"
                                    :aria-label="tallyAria(row)"
                                    :title="tallyAria(row)"
                                >
                                    <span
                                        v-for="segment in segments(row)"
                                        :key="segment.key"
                                        :class="['job-mini-segment', `job-tone-${segment.tone}`, { pending: segment.key === 'pending' }]"
                                        :style="{ width: `${segment.percent}%` }"
                                    ></span>
                                </span>
                                <span class="job-tally">{{ tallyLabel(row) }}</span>
                            </template>
                        </td>
                        <td class="cell-when">
                            <span :title="absolute(row.started || row.created)">{{ whenLabel(row) }}</span>
                        </td>
                        <td class="cell-duration">
                            {{ durationLabel(row) }}
                        </td>
                    </tr>
                </tbody>
                <tbody v-else>
                    <tr class="job-empty-row">
                        <td colspan="5">
                            <div class="job-empty">
                                <template v-if="filtered">
                                    <p class="job-empty-title">No job matches these filters</p>
                                    <b-button size="sm" variant="outline-secondary" @click="clearFilters">Clear filters</b-button>
                                </template>
                                <template v-else>
                                    <p class="job-empty-title">{{ emptyTitle }}</p>
                                    <p class="job-empty-text">
                                        Batch actions, quick actions on a selection, and changes made from a server
                                        page (plugin actions, user administration, sync connection edits) are
                                        recorded here, with their result on every server.
                                    </p>
                                </template>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div v-if="total > limit" class="job-pagination">
            <b-pagination
                v-model="page"
                :total-rows="total"
                :per-page="limit"
                size="sm"
                class="mb-0"
                aria-label="Pages of jobs"
            ></b-pagination>
        </div>
    </div>
</template>

<script>
import moment from "moment"
import { mapGetters } from "vuex"
import api from "@/api/jobs"
import JobStatusBadge from "@/components/jobs/JobStatusBadge.vue"
import {
    JOB_KIND_LABELS, JOB_PERIODS, JOB_STATUS_FILTERS, formatDuration, isFinalJob, jobTally, mergeJob,
} from "@/helpers/jobs"

const PAGE_SIZE = 25
const POLL_EVERY = 5  // seconds, for unfinished jobs of other users (their events go to their owner only)
const SEARCH_DELAY = 300
const REFETCH_DELAY = 600
const QUERY_KEYS = ["q", "status", "kind", "since", "scope", "fleet_id", "page"]

function emptyFilters() {
    return { status: "", kind: "", since: "", scope: "mine", fleet_id: null }
}

export default {
    name: "JobList",
    components: {
        JobStatusBadge,
    },
    props: {
        // Only the jobs of this fleet (fleet page) or that touched this server (server page)
        fleetId: {
            type: Number,
            default: null,
        },
        serverId: {
            type: Number,
            default: null,
        },
        // The global page: fleet column and filter, admins' scope switch, filters kept in the URL
        global: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        // The global page starts from the filters in its URL
        const initial = this.global ? this.initialFromQuery() : { filters: emptyFilters(), search: "", page: 1 }
        return {
            filters: initial.filters,
            search: initial.search,
            page: initial.page,
            limit: PAGE_SIZE,
            rows: [],
            total: 0,
            loaded: false,
            refreshing: false,
            error: null,
            newJobs: false,
            now: Date.now() / 1000,
            statusFilters: JOB_STATUS_FILTERS,
            periods: JOB_PERIODS.map(period => ({ value: period.value, text: period.text })),
            scopes: [
                { value: "mine", label: "Mine", help: "Jobs you started" },
                { value: "all", label: "Everyone", help: "Jobs of every user, including deleted users" },
            ],
        }
    },
    computed: {
        ...mapGetters({
            user: "auth/user",
            isAdmin: "auth/isAdmin",
            fleetList: "fleets/fleetList",
        }),
        showScope() {
            return this.global && this.isAdmin
        },
        showFleet() {
            return this.global || this.serverId !== null
        },
        showFleetFilter() {
            return this.global && this.filters.scope === "mine" && this.fleetList.length > 1
        },
        kindOptions() {
            return [{ value: "", text: "All kinds" }].concat(
                Object.keys(JOB_KIND_LABELS).map(kind => ({ value: kind, text: JOB_KIND_LABELS[kind] }))
            )
        },
        fleetOptions() {
            return [{ value: null, text: "All fleets" }].concat(
                this.fleetList.map(fleet => ({ value: fleet.id, text: fleet.name }))
            )
        },
        searchPlaceholder() {
            return this.filters.scope === "all" ? "Title, user, fleet or server" : "Title, fleet or server"
        },
        filtered() {
            const empty = emptyFilters()
            return this.search.trim() !== "" || ["status", "kind", "since", "fleet_id"].some(key => this.filters[key] !== empty[key])
        },
        countLabel() {
            if (this.total === 0) {
                return ""
            }
            if (this.total <= this.limit) {
                return `${this.total} job${this.total === 1 ? "" : "s"}`
            }
            const first = (this.page - 1) * this.limit + 1
            return `${first}–${Math.min(first + this.rows.length - 1, this.total)} of ${this.total}`
        },
        emptyTitle() {
            if (this.serverId) {
                return "No job has touched this server yet"
            }
            if (this.fleetId) {
                return "No job in this fleet yet"
            }
            return this.filters.scope === "all" ? "No job yet" : "You have not run any job yet"
        },
        myId() {
            return this.user ? this.user.id : null
        },
        apiParams() {
            const params = { page: this.page, limit: this.limit }
            const status = JOB_STATUS_FILTERS.find(option => option.value === this.filters.status)
            if (status && status.statuses.length) {
                params.status = status.statuses.join(",")
            }
            if (this.filters.kind) {
                params.kind = this.filters.kind
            }
            if (this.search.trim()) {
                params.q = this.search.trim()
            }
            if (this.showScope && this.filters.scope === "all") {
                params.scope = "all"
            }
            if (this.fleetId) {
                params.fleet_id = this.fleetId
            } else if (this.showFleetFilter && this.filters.fleet_id) {
                params.fleet_id = this.filters.fleet_id
            }
            if (this.serverId) {
                params.server_id = this.serverId
            }
            return params
        },
        // Everything that calls for a fresh first page
        filterKey() {
            return JSON.stringify([this.filters, this.fleetId, this.serverId])
        },
    },
    watch: {
        filterKey() {
            this.firstPage()
        },
        search() {
            clearTimeout(this.searchTimer)
            this.searchTimer = setTimeout(this.firstPage, SEARCH_DELAY)
        },
        page() {
            this.fetch()
        },
    },
    created() {
        this.requestSeq = 0
    },
    mounted() {
        this.fetch()
        this.unsubscribe = this.$store.subscribeAction({ after: this.onAction })
        this.ticks = 0
        this.ticker = setInterval(this.tick, 1000)
    },
    beforeDestroy() {
        if (this.unsubscribe) {
            this.unsubscribe()
        }
        clearInterval(this.ticker)
        clearTimeout(this.searchTimer)
        clearTimeout(this.refetchTimer)
    },
    methods: {
        kindLabel(kind) {
            return JOB_KIND_LABELS[kind] || kind
        },
        setFilter(key, value) {
            this.filters[key] = value
        },
        clearFilters() {
            const scope = this.filters.scope
            this.filters = Object.assign(emptyFilters(), { scope })
            this.search = ""
        },
        // The page watcher fetches when the page changes
        firstPage() {
            if (this.page === 1) {
                this.fetch()
            } else {
                this.page = 1
            }
        },
        showLatest() {
            this.newJobs = false
            this.firstPage()
        },
        initialFromQuery() {
            const query = this.$route.query
            const filters = emptyFilters()
            if (JOB_STATUS_FILTERS.some(option => option.value === query.status)) {
                filters.status = query.status
            }
            if (JOB_KIND_LABELS[query.kind]) {
                filters.kind = query.kind
            }
            if (JOB_PERIODS.some(period => period.value === query.since)) {
                filters.since = query.since
            }
            if (query.scope === "all" && this.$store.getters["auth/isAdmin"]) {
                filters.scope = "all"
            }
            const fleetId = Number.parseInt(query.fleet_id, 10)
            if (fleetId > 0) {
                filters.fleet_id = fleetId
            }
            const page = Number.parseInt(query.page, 10)
            return {
                filters,
                search: typeof query.q === "string" ? query.q : "",
                page: page > 1 ? page : 1,
            }
        },
        writeQuery() {
            if (!this.global) {
                return
            }
            const query = Object.assign({}, this.$route.query)
            QUERY_KEYS.forEach((key) => { delete query[key] })
            const values = {
                q: this.search.trim(),
                status: this.filters.status,
                kind: this.filters.kind,
                since: this.filters.since,
                scope: this.showScope && this.filters.scope === "all" ? "all" : "",
                fleet_id: this.showFleetFilter && this.filters.fleet_id ? String(this.filters.fleet_id) : "",
                page: this.page > 1 ? String(this.page) : "",
            }
            Object.keys(values).forEach((key) => {
                if (values[key]) {
                    query[key] = values[key]
                }
            })
            if (JSON.stringify(query) !== JSON.stringify(this.$route.query)) {
                this.$router.replace({ query }).catch(() => {})
            }
        },
        fetch({ silent = false } = {}) {
            const seq = ++this.requestSeq
            const params = Object.assign({}, this.apiParams)
            const period = JOB_PERIODS.find(option => option.value === this.filters.since)
            if (period && period.seconds) {
                params.since = Math.floor(Date.now() / 1000) - period.seconds
            }
            if (!silent) {
                this.refreshing = this.loaded
                this.writeQuery()
            }
            return api.index(params, (data) => {
                if (seq !== this.requestSeq) {
                    return
                }
                this.error = null
                this.total = data.total
                this.rows = this.mergeRows(data.jobs)
                if (this.page === 1) {
                    this.newJobs = false
                }
                // A page that no longer exists (jobs purged or filtered out): go back to the last one
                const lastPage = Math.max(1, Math.ceil(data.total / this.limit))
                if (this.page > lastPage) {
                    this.page = lastPage
                }
                this.loaded = true
                this.refreshing = false
            }, (error) => {
                if (seq !== this.requestSeq) {
                    return
                }
                this.refreshing = false
                if (!silent || !this.loaded) {
                    this.error = error
                    this.loaded = true
                }
            })
        },
        // Socket events and HTTP answers can arrive in any order: a row never goes back to an older state
        mergeRows(incoming) {
            const current = {}
            this.rows.forEach((row) => { current[row.id] = row })
            return incoming.map((job) => {
                const known = current[job.id]
                if (!known) {
                    return job
                }
                const merged = mergeJob(known, job)
                merged.done = Math.max(known.done || 0, job.done || 0)
                if (known.server_result && job.server_result && known.server_result.status !== "pending" &&
                        job.server_result.status === "pending") {
                    merged.server_result = known.server_result
                }
                return merged
            })
        },
        patchRow(job_id, patch) {
            const index = this.rows.findIndex(row => row.id === job_id)
            if (index === -1) {
                return false
            }
            const row = this.rows[index]
            if (isFinalJob(row) && patch.status && !isFinalJob(patch)) {
                return true  // A late event after the end
            }
            this.$set(this.rows, index, Object.assign({}, row, patch))
            return true
        },
        onAction(action) {
            // Several store modules handle SOCKET_CONNECT: only the jobs module's dispatch counts
            if (!action.type.startsWith("jobs/SOCKET_")) {
                return
            }
            const type = action.type.slice("jobs/".length)
            const payload = action.payload || {}
            if (type === "SOCKET_CONNECT") {
                this.fetch({ silent: true })
                return
            }
            if (!["SOCKET_JOB_STARTED", "SOCKET_JOB_PROGRESS", "SOCKET_JOB_DONE"].includes(type) || !payload.job_id) {
                return
            }
            let known = false
            if (type === "SOCKET_JOB_STARTED") {
                known = this.patchRow(payload.job_id, { status: "running", started: payload.started })
            } else if (type === "SOCKET_JOB_PROGRESS") {
                const row = this.rows.find(job => job.id === payload.job_id)
                if (row) {
                    const patch = {
                        status: "running",
                        done: Math.max(row.done || 0, payload.done || 0),
                        succeeded: Math.max(row.succeeded || 0, payload.succeeded || 0),
                        failed: Math.max(row.failed || 0, payload.failed || 0),
                    }
                    const result = payload.result
                    if (this.serverId && result && result.server_id === this.serverId) {
                        patch.server_result = Object.assign({}, result, { response: undefined, before: undefined })
                    }
                    this.patchRow(payload.job_id, patch)
                }
                return  // A job this page does not show announces itself with JOB_STARTED or JOB_DONE
            } else {
                known = this.patchRow(payload.job_id, {
                    status: payload.status, succeeded: payload.succeeded, failed: payload.failed,
                    finished: payload.finished, done: payload.total,
                })
                if (known && this.filters.status) {
                    this.scheduleRefetch()  // It may have left the filter
                }
            }
            if (!known) {
                // A new job (from this tab, another tab, or a change made from a server page)
                if (this.page === 1) {
                    this.scheduleRefetch()
                } else {
                    this.newJobs = true
                }
            }
        },
        scheduleRefetch() {
            clearTimeout(this.refetchTimer)
            this.refetchTimer = setTimeout(() => this.fetch({ silent: true }), REFETCH_DELAY)
        },
        tick() {
            this.ticks += 1
            const running = this.rows.some(row => !isFinalJob(row))
            if (running || this.ticks % 30 === 0) {
                this.now = Date.now() / 1000
            }
            // Other users' events go to them only: their running jobs, and on the first page of the "Everyone" view
            // their new jobs, are only seen by asking again
            const othersRunning = this.rows.some(row => !isFinalJob(row) && row.user_id !== this.myId)
            const othersNew = this.showScope && this.filters.scope === "all" && this.page === 1
            if ((othersRunning || othersNew) && this.ticks % POLL_EVERY === 0 && !document.hidden) {
                this.fetch({ silent: true })
            }
        },
        showUser(row) {
            return !row.user_id || row.user_id !== this.myId
        },
        openRow(event, row) {
            if (event.target.closest("a, button") || (window.getSelection && String(window.getSelection()))) {
                return
            }
            this.$router.push({ name: "jobs.view", params: { job_id: row.id } })
        },
        segments(row) {
            const tally = jobTally(row)
            const total = tally.total || 1
            const parts = [
                { key: "ok", tone: "ok", count: tally.ok },
                { key: "failed", tone: "critical", count: tally.failed },
                { key: "other", tone: "muted", count: tally.other },
            ]
            if (!isFinalJob(row)) {
                parts.push({ key: "pending", tone: "running", count: tally.pending })
            }
            return parts.filter(part => part.count > 0).map(part => Object.assign(part, { percent: 100 * part.count / total }))
        },
        tallyLabel(row) {
            const tally = jobTally(row)
            const parts = []
            if (!isFinalJob(row)) {
                return `${tally.done} / ${tally.total}`
            }
            if (tally.ok) {
                parts.push(`${tally.ok} OK`)
            }
            if (tally.failed) {
                parts.push(`${tally.failed} failed`)
            }
            if (tally.other) {
                parts.push(`${tally.other} not run`)  // Skipped or cancelled: the list does not tell them apart
            }
            return parts.join(" · ") || `${tally.total} server${tally.total === 1 ? "" : "s"}`
        },
        tallyAria(row) {
            const tally = jobTally(row)
            return `${tally.total} server${tally.total === 1 ? "" : "s"}: ${tally.ok} OK, ${tally.failed} failed` +
                (tally.other ? `, ${tally.other} not run (skipped or cancelled)` : "") +
                (tally.pending && !isFinalJob(row) ? `, ${tally.pending} pending` : "")
        },
        whenLabel(row) {
            if (!row.started) {
                return row.status === "queued" ? `Queued ${this.relative(row.created)}` : this.relative(row.created)
            }
            return this.relative(row.started)
        },
        relative(timestamp) {
            if (!timestamp) {
                return ""
            }
            // Re-evaluated on every tick of `now`
            return moment.unix(Math.min(timestamp, this.now)).from(moment.unix(this.now))
        },
        absolute(timestamp) {
            return timestamp ? moment.unix(timestamp).format("YYYY-MM-DD HH:mm:ss") : ""
        },
        durationLabel(row) {
            if (!row.started) {
                return "—"
            }
            const end = row.finished || (isFinalJob(row) ? row.started : this.now)
            return formatDuration(Math.max(end - row.started, 0)) || "—"
        },
    },
}
</script>

<style scoped>
.job-filters {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
}

.job-filter-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
}

.job-status-filter,
.job-scope {
    display: inline-flex;
    flex-wrap: wrap;
    padding: 2px;
    border-radius: 6px;
    background: #eef0f3;
}

.job-scope {
    margin-left: auto;
}

.job-status-option {
    border: none;
    background: none;
    padding: 0.2rem 0.7rem;
    border-radius: 4px;
    font-size: 0.82rem;
    font-weight: 600;
    color: #4a5260;
    line-height: 1.5;
}

.job-status-option:hover {
    color: var(--var-color-yankeesblue);
}

.job-status-option.active {
    background: #fff;
    color: var(--var-color-yankeesblue);
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.12);
}

.job-status-option:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 1px;
}

.job-search {
    flex: 1 1 220px;
    max-width: 340px;
}

.job-select {
    width: auto;
    flex: 0 1 auto;
    max-width: 200px;
}

.job-clear {
    padding-left: 0.25rem;
    padding-right: 0.25rem;
}

.job-list-count {
    margin-left: auto;
    font-size: 0.82rem;
    color: #5a6270;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}

.job-new-pill {
    display: block;
    margin: 0 auto 0.6rem;
    border: none;
    border-radius: 999px;
    padding: 0.25rem 0.9rem;
    font-size: 0.82rem;
    font-weight: 600;
    color: #fff;
    background: var(--var-color-lapislazuli);
    box-shadow: 0 2px 6px rgba(16, 24, 40, 0.18);
}

.job-new-pill:focus-visible {
    outline: 2px solid var(--var-color-yankeesblue);
    outline-offset: 2px;
}

.job-table-wrap {
    background: #fff;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    overflow: hidden;
    position: relative;
}

/* A thin moving line while a page reloads, instead of blanking the table */
.job-table-wrap.is-refreshing::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    height: 2px;
    width: 30%;
    background: var(--var-color-lapislazuli);
    animation: job-refresh 1s ease-in-out infinite;
    z-index: 1;
}

@keyframes job-refresh {
    from { left: -30%; }
    to { left: 100%; }
}

.job-table {
    width: 100%;
    table-layout: fixed;
    border-collapse: collapse;
    font-size: 0.875rem;
}

.col-status { width: 132px; }
.col-servers { width: 240px; }
.col-when { width: 150px; }
.col-duration { width: 96px; }

.job-table th {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #5a6270;
    background: #f7f8fa;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--health-rule);
}

.job-table td {
    padding: 0.55rem 0.75rem;
    border-top: 1px solid #eef0f3;
    vertical-align: middle;
}

.job-table tbody tr:first-child td {
    border-top: none;
}

.job-row {
    cursor: pointer;
}

.job-row:hover td {
    background: #f7fafc;
}

.cell-job {
    min-width: 0;
}

.job-link {
    display: block;
    font-weight: 600;
    color: var(--var-color-yankeesblue);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.job-link:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 2px;
}

.job-row-meta {
    font-size: 0.78rem;
    color: #5f6873;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.is-gone {
    font-style: italic;
}

.dot {
    margin: 0 0.3rem;
}

/* "2 OK · 1 failed · 1 not run" may not fit beside the bar: it wraps rather than run into the next column */
.cell-servers {
    white-space: normal;
}

.job-mini-bar {
    display: inline-flex;
    vertical-align: middle;
    width: 64px;
    height: 6px;
    border-radius: 3px;
    background: #eef0f3;
    overflow: hidden;
    margin-right: 0.5rem;
}

.job-mini-segment {
    height: 100%;
    background: var(--job-fill);
    transition: width 0.3s ease;
}

.job-mini-segment.pending {
    opacity: 0.25;
}

.job-tally,
.job-tally-small {
    font-size: 0.8rem;
    color: #4a5260;
    font-variant-numeric: tabular-nums;
}

.job-tally-small {
    display: block;
    color: #6c757d;
    margin-top: 0.1rem;
}

.server-result {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    min-width: 0;
}

.server-result-summary {
    font-size: 0.78rem;
    color: #5f6873;
    overflow: hidden;
    text-overflow: ellipsis;
}

.cell-when {
    color: #4a5260;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.cell-duration {
    text-align: right;
    color: #4a5260;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}

.job-empty {
    padding: 2.5rem 1rem;
    text-align: center;
    color: #5a6270;
}

.job-empty-title {
    font-weight: 700;
    color: var(--var-color-yankeesblue);
    margin-bottom: 0.4rem;
}

.job-empty-text {
    max-width: 520px;
    margin: 0 auto;
    font-size: 0.85rem;
}

.job-pagination {
    display: flex;
    justify-content: center;
    margin-top: 0.75rem;
}

/* Skeleton rows on the first load */
.job-skeleton td {
    cursor: default;
}

.bone {
    display: block;
    height: 0.7rem;
    border-radius: 3px;
    background: linear-gradient(90deg, #eef0f3 25%, #f6f7f9 50%, #eef0f3 75%);
    background-size: 200% 100%;
    animation: job-bone 1.4s ease-in-out infinite;
}

.bone-badge { width: 72px; height: 1.1rem; border-radius: 999px; }
.bone-title { width: 55%; height: 0.85rem; margin-bottom: 0.35rem; }
.bone-meta { width: 30%; }
.bone-bar { width: 120px; }
.bone-short { width: 60px; }

@keyframes job-bone {
    from { background-position: 200% 0; }
    to { background-position: -200% 0; }
}

@media (prefers-reduced-motion: reduce) {
    .bone,
    .job-table-wrap.is-refreshing::before {
        animation: none;
    }
    .job-mini-segment {
        transition: none;
    }
}

/* Narrow screens: each job is a small card */
@media (max-width: 767.98px) {
    .job-scope {
        margin-left: 0;
    }

    .job-search,
    .job-select {
        max-width: none;
        flex: 1 1 140px;
    }

    .job-list-count {
        width: 100%;
        margin-left: 0;
    }

    .job-table colgroup,
    .job-table thead {
        display: none;
    }

    .job-table,
    .job-table tbody {
        display: block;
    }

    .job-table tr.job-row,
    .job-table tr.job-skeleton {
        display: grid;
        grid-template-columns: 1fr auto;
        grid-template-areas:
            "job status"
            "servers servers"
            "when duration";
        gap: 0.3rem 0.75rem;
        padding: 0.7rem 0.85rem;
        border-top: 1px solid #eef0f3;
    }

    .job-table tbody tr:first-child {
        border-top: none;
    }

    .job-table tr.job-row td,
    .job-table tr.job-skeleton td {
        display: block;
        padding: 0;
        border: none;
        min-width: 0;
    }

    /* Room is short: titles wrap rather than lose their end (server names, URLs) */
    .job-link,
    .job-row-meta {
        white-space: normal;
        overflow-wrap: anywhere;
    }

    .job-table td:nth-child(1) { grid-area: status; }
    .job-table td:nth-child(2) { grid-area: job; }
    .job-table td:nth-child(3) { grid-area: servers; }
    .job-table td:nth-child(4) { grid-area: when; font-size: 0.8rem; }
    .job-table td:nth-child(5) { grid-area: duration; font-size: 0.8rem; }

    .job-table tr.job-empty-row,
    .job-table tr.job-empty-row td {
        display: block;
        border: none;
    }
}
</style>
