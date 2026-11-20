<template>
<Layout name="LayoutDefault">
    <div class="page-container query-page">
        <header class="q-header">
            <div>
                <h1 class="q-title">Query</h1>
                <p class="q-lede">
                    Ask many MISP servers the same question in MispQL, a read-only SQL-like language. Each server is
                    asked with its own key, so MISP applies that user's access. Rows are kept {{ ttlLabel }}, for you only.
                </p>
            </div>
            <b-dropdown right variant="outline-secondary" size="sm" class="q-recent" @show="loadRecent">
                <template #button-content>
                    <i class="fas fa-clock-rotate-left mr-1" aria-hidden="true"></i>Recent runs
                </template>
                <b-dropdown-text v-if="recentLoading && recent.length === 0" class="q-recent-note">
                    <b-spinner small class="mr-1"></b-spinner>Loading…
                </b-dropdown-text>
                <b-dropdown-text v-else-if="recentError" class="q-recent-note text-danger">{{ recentError }}</b-dropdown-text>
                <b-dropdown-text v-else-if="recent.length === 0" class="q-recent-note">No runs yet.</b-dropdown-text>
                <b-dropdown-item
                    v-for="job in recent"
                    :key="job.id"
                    :to="{ name: 'query', params: { job_id: job.id } }"
                    :active="job.id === job_id"
                    link-class="q-recent-item"
                >
                    <span :class="['q-recent-dot', `job-tone-${statusMeta(job.status).tone}`]" :title="statusMeta(job.status).label"></span>
                    <span class="q-recent-title">{{ job.title }}</span>
                    <span class="q-recent-when">{{ relative(job.created) }}</span>
                </b-dropdown-item>
                <b-dropdown-divider></b-dropdown-divider>
                <b-dropdown-item :to="{ name: 'jobs', query: { kind: 'mispql_query' } }">
                    <i class="fas fa-list-check fa-fw mr-1" aria-hidden="true"></i>Every query run, on the Jobs page
                </b-dropdown-item>
            </b-dropdown>
        </header>

        <section class="q-composer" aria-label="Statement and servers">
            <div class="q-targets">
                <span class="q-targets-label" id="q-targets-label">On</span>
                <button
                    type="button"
                    class="q-target-button"
                    aria-controls="q-picker"
                    :aria-expanded="pickerOpen ? 'true' : 'false'"
                    aria-describedby="q-targets-label"
                    @click="pickerOpen = !pickerOpen"
                >
                    <i class="fas fa-server" aria-hidden="true"></i>
                    <span>{{ targetLabel }}</span>
                    <i :class="['fas', pickerOpen ? 'fa-chevron-up' : 'fa-chevron-down', 'q-chevron']" aria-hidden="true"></i>
                </button>
                <span v-if="selection.supported > 0" class="q-stat job-tone-ok">
                    <i class="fas fa-circle-check" aria-hidden="true"></i>{{ selection.supported }} can run queries
                </span>
                <span v-if="selection.skipped > 0" class="q-stat job-tone-muted" :title="skippedTitle">
                    <i class="fas fa-ban" aria-hidden="true"></i>{{ selection.skipped }} can't run queries
                </span>
                <span v-if="selection.checking > 0" class="q-stat job-tone-muted">
                    <i class="fas fa-spinner fa-spin" aria-hidden="true"></i>{{ selection.checking }} being checked
                </span>
            </div>
            <b-collapse id="q-picker" v-model="pickerOpen" class="q-picker">
                <QueryServerPicker
                    v-model="selected"
                    :fleets="fleets"
                    :capabilities="capabilities"
                    :checking="checkingCapabilities"
                    @recheck="loadCapabilities(true)"
                ></QueryServerPicker>
            </b-collapse>

            <QueryEditor
                ref="editor"
                v-model="statement"
                :language="language"
                :described="described"
                :marks="editorMarks"
                describedby="q-status"
                placeholder="SELECT * FROM attributes WHERE value = '198.51.100.23'"
                @run="startRun"
            ></QueryEditor>

            <div class="q-footer">
                <div id="q-status" :class="['q-status', `q-status-${status.tone}`]" aria-live="polite">
                    <i :class="['fas', status.icon]" aria-hidden="true"></i>
                    <span>{{ status.text }}</span>
                </div>
                <div class="q-footer-actions">
                    <b-button
                        variant="link"
                        size="sm"
                        class="q-clear"
                        :disabled="!canClear"
                        title="Clear the statement and the results. Ctrl+Z brings the statement back, Back the results"
                        @click="clearAll"
                    >
                        <i class="fas fa-eraser mr-1" aria-hidden="true"></i>Clear
                    </b-button>
                    <b-dropdown variant="link" size="sm" right class="q-examples" toggle-class="q-examples-toggle">
                        <template #button-content>Examples</template>
                        <b-dropdown-item-button v-for="example in examples" :key="example.title" @click="useExample(example)">
                            <span class="q-example-title">{{ example.title }}</span>
                            <code class="q-example-code">{{ oneLine(example.statement) }}</code>
                        </b-dropdown-item-button>
                    </b-dropdown>
                    <b-button
                        variant="primary"
                        class="q-run"
                        :disabled="!canRun"
                        :title="runBlocker || null"
                        @click="startRun"
                    >
                        <b-spinner v-if="starting" small class="mr-1"></b-spinner>
                        <i v-else class="fas fa-play mr-1" aria-hidden="true"></i>Run
                        <kbd class="q-kbd">{{ runShortcut }}</kbd>
                    </b-button>
                </div>
            </div>
            <p v-if="runBlocker && statement.trim() && !starting" class="q-blocker">{{ runBlocker }}</p>
            <div v-if="refused.length" class="q-refused">
                <QueryErrorList :statement="refusedStatement" :groups="refused" locatable @locate="locate"></QueryErrorList>
            </div>
        </section>

        <section v-if="job_id" class="q-results" aria-label="Results">
            <div v-if="runLoading && !job" class="q-state"><b-spinner small class="mr-2"></b-spinner>Loading the run…</div>
            <div v-else-if="runNotFound" class="q-state">
                <h2 class="q-state-title">Run not found</h2>
                <p>It may have been removed by the jobs' retention, or it belongs to someone else.</p>
            </div>
            <b-alert v-else-if="runError && !job" show variant="danger">
                Could not load the run: {{ runError }}
                <b-button size="sm" variant="outline-danger" class="ml-2" @click="loadRun">Try again</b-button>
            </b-alert>

            <template v-else-if="job">
                <header class="q-run-header">
                    <div class="q-run-heading">
                        <div class="q-run-meta">
                            <span :class="['q-run-status', `job-tone-${statusMeta(job.status).tone}`]">
                                <i v-if="!final" class="fas fa-spinner fa-spin" aria-hidden="true"></i>
                                {{ statusMeta(job.status).label }}
                            </span>
                            <span :title="absolute(job.created)">{{ relative(job.created) }}</span>
                            <span class="dot" aria-hidden="true">·</span>
                            <span>{{ job.total }} server{{ job.total === 1 ? '' : 's' }}</span>
                            <template v-if="runDuration">
                                <span class="dot" aria-hidden="true">·</span>
                                <span>{{ runDuration }}</span>
                            </template>
                            <template v-if="!own && job.user_email">
                                <span class="dot" aria-hidden="true">·</span>
                                <span>by {{ job.user_email }}</span>
                            </template>
                        </div>
                        <pre v-if="runStatement && !editorMatchesRun" class="q-run-statement" title="The statement of this run">{{ runStatement }}</pre>
                    </div>
                    <div class="q-run-actions">
                        <b-button v-if="!final" size="sm" variant="outline-danger" :disabled="cancelRequested" @click="cancel">
                            <i class="fas fa-ban mr-1" aria-hidden="true"></i>{{ cancelRequested ? 'Cancelling…' : 'Cancel' }}
                        </b-button>
                        <b-button
                            v-if="runStatement && !editorMatchesRun"
                            size="sm"
                            variant="outline-secondary"
                            @click="statement = runStatement"
                        >Back to this statement</b-button>
                        <b-button size="sm" variant="link" :to="{ name: 'jobs.view', params: { job_id: job.id } }">Job page</b-button>
                    </div>
                </header>

                <div v-if="!final" class="q-progress" role="progressbar" :aria-valuenow="job.done || 0" aria-valuemin="0" :aria-valuemax="job.total">
                    <span :style="{ width: `${progress}%` }"></span>
                </div>

                <QueryRunServers
                    :results="results"
                    :kind="runKind"
                    :active-server="rowServer"
                    :filterable="runKind === 'select' && final && rowsReadable"
                    @filter="rowServer = $event"
                ></QueryRunServers>

                <div v-if="errorGroups.length" class="q-block">
                    <h2 class="q-block-title">Mistakes MISP found</h2>
                    <QueryErrorList
                        :statement="runStatement"
                        :groups="errorGroups"
                        :total="results.length"
                        :locatable="editorMatchesRun"
                        @locate="locate"
                    ></QueryErrorList>
                </div>

                <div v-if="runKind === 'select' && (!final || rowServers > 0)" class="q-block">
                    <h2 class="q-block-title">Rows</h2>
                    <p v-if="!final" class="q-note"><b-spinner small class="mr-1"></b-spinner>Rows appear when every server has answered.</p>
                    <p v-else-if="!rowsReadable" class="q-note">
                        <i class="fas fa-lock mr-1" aria-hidden="true"></i>Only the user who ran this query can read its
                        rows: they were fetched with that user's keys.
                    </p>
                    <template v-else>
                        <p v-if="rowNotes.length" class="q-note">
                            <i class="fas fa-circle-info mr-1" aria-hidden="true"></i>{{ rowNotes.join(' ') }}
                        </p>
                        <QueryRowsTable
                            :job-id="job.id"
                            :results="results"
                            :server-id.sync="rowServer"
                            :table="runTable"
                        ></QueryRowsTable>
                    </template>
                </div>

                <div v-if="runKind === 'describe' || runKind === 'show_tables'" class="q-block">
                    <h2 class="q-block-title">{{ runKind === 'describe' ? `Fields of ${runTable}` : 'Tables' }}</h2>
                    <QueryMatrix :kind="runKind" :results="results" :table-order="tableOrder"></QueryMatrix>
                </div>
            </template>
        </section>

        <section v-else class="q-empty" aria-label="How queries run">
            <div class="q-empty-item">
                <i class="fas fa-key" aria-hidden="true"></i>
                <div>
                    <strong>Each server answers as its key's user</strong>
                    <p>MISP applies that user's access to every condition. Statements only read: SELECT, COUNT(*), DESCRIBE and SHOW TABLES.</p>
                </div>
            </div>
            <div class="q-empty-item">
                <i class="fas fa-ban" aria-hidden="true"></i>
                <div>
                    <strong>Servers without complex queries are skipped</strong>
                    <p>An older MISP would ignore the WHERE and answer as if there were none, so it is never searched.</p>
                </div>
            </div>
            <div class="q-empty-item">
                <i class="fas fa-layer-group" aria-hidden="true"></i>
                <div>
                    <strong>Answers side by side</strong>
                    <p>Rows merged with their server, counts with a total, fields and tables per server. LIMIT, OFFSET and ORDER BY apply on each server.</p>
                </div>
            </div>
        </section>
    </div>
</Layout>
</template>

<script>
import moment from "moment"
import Layout from "@/components/layout/Layout.vue"
import QueryEditor from "@/components/query/QueryEditor.vue"
import QueryServerPicker from "@/components/query/QueryServerPicker.vue"
import QueryRunServers from "@/components/query/QueryRunServers.vue"
import QueryErrorList from "@/components/query/QueryErrorList.vue"
import QueryRowsTable from "@/components/query/QueryRowsTable.vue"
import QueryMatrix from "@/components/query/QueryMatrix.vue"
import api from "@/api/queries"
import { formatDuration, isFinalJob, jobStatusMeta } from "@/helpers/jobs"
import {
    EXAMPLES, capabilityMeta, groupErrors, statementKind, statementTable, unionFields,
} from "@/helpers/mispql"

const DRAFT_KEY = "mfc.query.draft"
const CHECK_DELAY = 350
const DESCRIBE_DELAY = 400
const POLL_INTERVAL = 3000
const KIND_TEXT = {
    count: table => `A count of ${table} on each server`,
    describe: table => `The fields of ${table} on each server`,
    show_tables: () => "The tables each server answers",
}

function readDraft() {
    try {
        return window.localStorage.getItem(DRAFT_KEY) || ""
    } catch (e) {
        return ""
    }
}

function saveDraft(text) {
    try {
        window.localStorage.setItem(DRAFT_KEY, text)
    } catch (e) {
        // Private windows and blocked storage: the draft is a convenience
    }
}

function idsFrom(value) {
    return String(value || "").split(",").map(part => Number.parseInt(part, 10)).filter(id => !Number.isNaN(id))
}

// One MispQL statement run on many servers: the statement with its servers, then the run's answers by server
export default {
    name: "QueryPage",
    components: {
        Layout,
        QueryEditor,
        QueryServerPicker,
        QueryRunServers,
        QueryErrorList,
        QueryRowsTable,
        QueryMatrix,
    },
    props: {
        // The run shown, if any
        job_id: { type: String, default: null },
    },
    data() {
        return {
            language: null,
            statement: readDraft(),
            check: null,
            checking: false,
            checkRequest: 0,
            fleets: [],
            capabilities: {},
            checkingCapabilities: false,
            selected: [],
            pickerOpen: false,
            describedByKey: {},
            starting: false,
            refused: [],
            refusedStatement: "",
            run: null,
            runLoading: false,
            runNotFound: false,
            runError: null,
            startedJobId: null,
            cancelRequested: false,
            rowServer: null,
            recent: [],
            recentLoading: false,
            recentError: null,
            examples: EXAMPLES,
        }
    },
    computed: {
        ttlLabel() {
            const minutes = Number(this.$store.getters["settings/settingValues"].query_rows_ttl_minutes) || null
            return minutes ? `for ${minutes} minute${minutes === 1 ? "" : "s"}` : "for a while"
        },
        runShortcut() {
            return /Mac|iPhone|iPad/.test(navigator.platform || "") ? "⌘↵" : "Ctrl ↵"
        },
        servers() {
            return this.fleets.flatMap(fleet => fleet.servers.map(server => Object.assign({ fleet_id: fleet.id, fleet_name: fleet.name }, server)))
        },
        serversById() {
            const byId = {}
            this.servers.forEach((server) => { byId[server.id] = server })
            return byId
        },
        selection() {
            const counts = { total: 0, supported: 0, skipped: 0, checking: 0 }
            this.selected.forEach((id) => {
                counts.total += 1
                const found = this.capabilities[id]
                if (!found) {
                    counts.checking += 1
                } else if (found.state === "supported") {
                    counts.supported += 1
                } else {
                    counts.skipped += 1
                }
            })
            return counts
        },
        // Who can't, and why: a run still asks them, and says what they answered
        skippedTitle() {
            return this.selected.filter(id => this.capabilities[id] && this.capabilities[id].state !== "supported")
                .map(id => `${(this.serversById[id] || {}).name || id}: ${capabilityMeta(this.capabilities[id].state).short}`)
                .join("\n")
        },
        targetLabel() {
            const count = this.selected.length
            if (count === 0) {
                return "Choose servers"
            }
            const fleetIds = new Set(this.selected.map(id => (this.serversById[id] || {}).fleet_id).filter(Boolean))
            const servers = `${count} server${count === 1 ? "" : "s"}`
            if (fleetIds.size === 1) {
                const fleet = this.fleets.find(entry => fleetIds.has(entry.id))
                if (fleet) {
                    return count === fleet.servers.length ? `${fleet.name} · all ${servers}` : `${fleet.name} · ${servers}`
                }
            }
            return fleetIds.size > 1 ? `${servers} in ${fleetIds.size} fleets` : servers
        },
        // The table of the statement being written, as soon as it is typed
        table() {
            return (this.check && this.check.ok && this.check.table) || statementTable(this.statement, 0, this.language ? this.language.keywords : undefined)
        },
        describeServers() {
            return this.selected.filter(id => (this.capabilities[id] || {}).state === "supported").slice().sort((a, b) => a - b)
        },
        describeKey() {
            const known = this.language && this.language.tables.some(entry => entry.name === this.table)
            return known && this.describeServers.length ? `${this.table}:${this.describeServers.join(",")}` : null
        },
        described() {
            return this.describeKey ? this.describedByKey[this.describeKey] || null : null
        },
        status() {
            if (!this.statement.trim()) {
                return { tone: "muted", icon: "fa-keyboard", text: "Write a statement. Ctrl+Space completes it, and the Examples show what it can ask." }
            }
            if (!this.check) {
                return { tone: "muted", icon: "fa-spinner fa-spin", text: "Checking…" }
            }
            if (!this.check.ok) {
                const error = this.check.errors[0] || { message: "Invalid statement" }
                const where = error.line ? ` (line ${error.line}, column ${error.column})` : ""
                return { tone: "error", icon: "fa-triangle-exclamation", text: `${error.message}${where}` }
            }
            if (this.check.kind === "select") {
                const limit = this.check.limit_added
                    ? `no LIMIT, so at most ${this.check.limit} rows per server`
                    : `at most ${this.check.limit} row${this.check.limit === 1 ? "" : "s"} per server`
                return { tone: "ok", icon: "fa-circle-check", text: `Rows of ${this.check.table}: ${limit}` }
            }
            const text = KIND_TEXT[this.check.kind]
            return { tone: "ok", icon: "fa-circle-check", text: text ? text(this.check.table) : "Ready" }
        },
        runBlocker() {
            if (!this.statement.trim()) {
                return "Write a statement first."
            }
            if (this.check && !this.check.ok) {
                return "Fix the statement first."
            }
            if (this.selected.length === 0) {
                return "Choose the servers to ask."
            }
            if (this.selection.checking === 0 && this.selection.supported === 0) {
                return "None of the chosen servers can run complex queries."
            }
            return ""
        },
        canClear() {
            return this.statement !== "" || Boolean(this.job_id) || this.refused.length > 0
        },
        canRun() {
            return !this.runBlocker && !this.starting && !this.checking
        },
        editorMarks() {
            if (this.check && !this.check.ok) {
                return this.check.errors
            }
            if (this.refused.length && this.statement === this.refusedStatement) {
                return this.refused
            }
            return this.editorMatchesRun ? this.errorGroups : []
        },
        // The run, live: its job from the store (socket events) with what only the run's view says
        job() {
            return this.job_id ? (this.$store.getters["jobs/job"](this.job_id) || this.run) : null
        },
        final() {
            return isFinalJob(this.job)
        },
        running() {
            return Boolean(this.job) && !this.final
        },
        own() {
            const user = this.$store.getters["auth/user"]
            return !this.job || (user !== null && this.job.user_id === user.id)
        },
        results() {
            const kept = {}
            ;((this.run && this.run.results) || []).forEach((result) => { kept[result.id] = result.rows_kept })
            return ((this.job && this.job.results) || []).map(result => Object.assign({}, result, { rows_kept: kept[result.id] }))
        },
        runStatement() {
            return (this.run && this.run.statement) || (this.job && this.job.params && this.job.params.statement) || ""
        },
        editorMatchesRun() {
            return Boolean(this.runStatement) && this.statement === this.runStatement
        },
        runSummaries() {
            return this.results.map(result => result.response).filter(Boolean)
        },
        runKind() {
            const found = this.runSummaries.find(summary => summary.kind)
            return found ? found.kind : statementKind(this.runStatement)
        },
        runTable() {
            const found = this.runSummaries.find(summary => summary.table)
            return found ? found.table : null
        },
        rowsReadable() {
            return !this.run || this.run.rows_readable !== false
        },
        rowServers() {
            return this.runSummaries.filter(summary => summary.outcome === "rows").length
        },
        rowNotes() {
            const notes = []
            const rows = this.runSummaries.filter(summary => summary.outcome === "rows")
            if (rows.some(summary => summary.limit_added)) {
                notes.push(`The statement had no LIMIT: each server returned at most ${rows[0].limit} rows.`)
            }
            const more = rows.filter(summary => summary.more).length
            if (more) {
                notes.push(`${more} server${more === 1 ? " has" : "s have"} more rows than the LIMIT: narrow the WHERE, or page with OFFSET.`)
            }
            if (this.runStatement && /\border\s+by\b/i.test(this.runStatement)) {
                notes.push("Sorted again across servers by the ORDER BY.")
            }
            return notes
        },
        errorGroups() {
            return groupErrors(this.results)
        },
        progress() {
            return this.job && this.job.total ? Math.round(((this.job.done || 0) / this.job.total) * 100) : 0
        },
        runDuration() {
            if (!this.job || !this.job.started) {
                return ""
            }
            const end = this.job.finished || (Date.now() / 1000)
            return this.final ? formatDuration(end - this.job.started) : ""
        },
        tableOrder() {
            return this.language ? this.language.tables.map(entry => entry.name) : []
        },
        needsPolling() {
            return Boolean(this.job) && !this.final && !this.own
        },
    },
    watch: {
        statement(text) {
            saveDraft(text)
            if (text !== this.refusedStatement) {
                this.refused = []  // its places were on the text as it was
            }
            this.scheduleCheck()
        },
        job_id() {
            this.cancelRequested = false
            this.rowServer = null
            this.loadRun()
        },
        // A run seen running has just ended: which servers' rows are kept, and the recent runs, change
        running(now, before) {
            if (before && !now && this.job) {
                this.cancelRequested = false
                this.refreshRun()
                this.loadRecent()
            }
        },
        describeKey(key) {
            clearTimeout(this.describeTimer)
            if (key && !this.describedByKey[key]) {
                this.describeTimer = setTimeout(() => this.loadDescribe(key), DESCRIBE_DELAY)
            }
        },
        needsPolling: {
            handler(needed) {
                clearInterval(this.pollTimer)
                if (needed) {
                    this.pollTimer = setInterval(() => {
                        this.$store.dispatch("jobs/fetch", this.job_id).catch(() => {})
                    }, POLL_INTERVAL)
                }
            },
            immediate: true,
        },
    },
    created() {
        api.language().then((language) => { this.language = language }).catch(() => {})
        this.loadFleets()
        if (this.statement.trim()) {
            this.scheduleCheck(0)
        }
        if (this.job_id) {
            this.loadRun()
        }
    },
    beforeDestroy() {
        clearTimeout(this.checkTimer)
        clearTimeout(this.describeTimer)
        clearInterval(this.pollTimer)
    },
    methods: {
        statusMeta(status) {
            return jobStatusMeta(status)
        },
        relative(timestamp) {
            return timestamp ? moment.unix(timestamp).fromNow() : ""
        },
        absolute(timestamp) {
            return timestamp ? moment.unix(timestamp).format("YYYY-MM-DD HH:mm:ss") : ""
        },
        oneLine(text) {
            return text.replace(/\s+/g, " ")
        },
        // The servers chosen when the page opens: the run's, those named in the URL, else the selected fleet's
        initialSelection() {
            const query = this.$route.query
            if (query.servers) {
                return idsFrom(query.servers)
            }
            const fleetId = Number.parseInt(query.fleet, 10)
            const fleet = !Number.isNaN(fleetId) ? this.fleets.find(entry => entry.id === fleetId) : null
            if (fleet) {
                return fleet.servers.map(server => server.id)
            }
            const current = this.$store.getters["fleets/selectedFleet"]
            const selectedFleet = current ? this.fleets.find(entry => entry.id === current.id) : null
            return selectedFleet ? selectedFleet.servers.map(server => server.id) : []
        },
        loadFleets() {
            api.fleets().then((fleets) => {
                this.fleets = (fleets || []).map(fleet => ({ id: fleet.id, name: fleet.name, servers: [], loading: true, error: null }))
                    .sort((a, b) => a.name.localeCompare(b.name))
                if (this.fleets.length === 0) {
                    this.pickerOpen = true
                }
                return Promise.all(this.fleets.map(fleet => this.loadFleetServers(fleet)))
            }).then(() => {
                if (!this.selected.length && !this.startedJobId && !(this.run && this.adoptRun(this.run))) {
                    this.selected = this.initialSelection().filter(id => this.serversById[id])
                }
                if (this.selected.length === 0) {
                    this.pickerOpen = true
                }
            }).catch((error) => {
                this.$bvToast.toast(String(error), { title: "Could not load your fleets", variant: "danger", solid: true })
            })
        },
        loadFleetServers(fleet) {
            return api.serversOfFleet(fleet.id).then((servers) => {
                fleet.servers = (servers || []).map(server => ({ id: server.id, name: server.name, url: server.url }))
                    .sort((a, b) => a.name.localeCompare(b.name))
                fleet.loading = false
                this.loadCapabilitiesOf(fleet.servers.map(server => server.id), false)
            }).catch((error) => {
                fleet.loading = false
                fleet.error = String(error)
            })
        },
        loadCapabilitiesOf(ids, refresh) {
            if (ids.length === 0) {
                return Promise.resolve()
            }
            if (refresh) {
                ids.forEach(id => this.$delete(this.capabilities, id))
            }
            return api.capabilities({ server_ids: ids, refresh }).then((answer) => {
                (answer.servers || []).forEach((entry) => {
                    this.$set(this.capabilities, entry.server_id, entry)
                })
            }).catch(() => {
                ids.forEach(id => this.$set(this.capabilities, id, { state: "unknown", detail: "Could not ask" }))
            })
        },
        loadCapabilities(refresh) {
            this.checkingCapabilities = true
            const byFleet = this.fleets.map(fleet => this.loadCapabilitiesOf(fleet.servers.map(server => server.id), refresh))
            Promise.all(byFleet).finally(() => {
                this.checkingCapabilities = false
            })
        },
        loadDescribe(key) {
            const [table] = key.split(":")
            api.describe({ table, server_ids: this.describeServers }).then((answer) => {
                this.$set(this.describedByKey, key, unionFields(answer.servers))
            }).catch(() => {
                this.$set(this.describedByKey, key, unionFields([]))
            })
        },
        scheduleCheck(delay = CHECK_DELAY) {
            clearTimeout(this.checkTimer)
            this.check = null
            if (!this.statement.trim()) {
                this.checking = false
                return
            }
            this.checking = true
            this.checkTimer = setTimeout(this.runCheck, delay)
        },
        runCheck() {
            this.checkRequest += 1
            const request = this.checkRequest
            const text = this.statement
            api.check(text).then((check) => {
                if (request === this.checkRequest && text === this.statement) {
                    this.check = check
                }
            }).catch((error) => {
                if (request === this.checkRequest) {
                    this.check = { ok: true, errors: [], kind: null, unchecked: String(error) }
                }
            }).finally(() => {
                if (request === this.checkRequest) {
                    this.checking = false
                }
            })
        },
        // An empty editor and no results; the servers stay chosen. The run itself goes on if it was running: it is
        // still in the recent runs and on the Jobs page
        clearAll() {
            this.refused = []
            this.rowServer = null
            this.startedJobId = null  // Back to the run then brings its statement back too
            this.$refs.editor.clear()
            if (this.job_id) {
                this.$router.push({ name: "query" }).catch(() => {})
            }
        },
        useExample(example) {
            this.statement = example.statement
            this.$nextTick(() => this.$refs.editor.focus())
        },
        locate(error) {
            if (!this.editorMatchesRun && this.statement !== this.refusedStatement) {
                return
            }
            const input = this.$refs.editor.$refs.input
            input.focus()
            input.setSelectionRange(error.start, Math.max(error.start, error.end))
        },
        startRun() {
            if (!this.canRun) {
                return
            }
            this.starting = true
            this.refused = []
            const statement = this.statement
            api.run({ statement, server_ids: this.selected }).then((answer) => {
                if (!answer.ok) {
                    this.refused = answer.errors || []
                    this.refusedStatement = statement
                    if (!this.refused.length) {
                        this.$bvToast.toast(answer.message || "The statement cannot run", { title: "Not run", variant: "danger", solid: true })
                    }
                    return
                }
                this.$store.commit("jobs/setJob", answer.job)
                this.startedJobId = answer.job_id
                this.pickerOpen = false
                this.$router.push({ name: "query", params: { job_id: answer.job_id } }).catch(() => {})
                this.loadRecent()
            }).catch((error) => {
                this.$bvToast.toast(String(error), { title: "Could not run the query", variant: "danger", solid: true })
            }).finally(() => {
                this.starting = false
            })
        },
        // A run opened from a link: its statement and its servers (those the user still has) in the composer
        adoptRun(run) {
            if (!this.own || !this.fleets.length || this.fleets.some(fleet => fleet.loading)) {
                return false
            }
            const ids = (run.results || []).map(result => result.server_id).filter(id => this.serversById[id])
            if (ids.length) {
                this.selected = ids
            }
            return true
        },
        loadRun() {
            if (!this.job_id) {
                this.run = null
                return
            }
            const job_id = this.job_id
            const ours = this.startedJobId === job_id
            this.runLoading = true
            this.runNotFound = false
            this.runError = null
            this.run = null
            this.$store.dispatch("jobs/fetch", job_id).catch(() => {})
            api.get(job_id).then((run) => {
                if (job_id !== this.job_id) {
                    return
                }
                this.run = run
                if (!ours) {
                    if (run.statement && run.statement !== this.statement) {
                        this.statement = run.statement
                    }
                    this.adoptRun(run)
                }
            }).catch((error) => {
                if (job_id !== this.job_id) {
                    return
                }
                if (/unknown/i.test(String(error))) {
                    this.runNotFound = true
                } else {
                    this.runError = String(error)
                }
            }).finally(() => {
                if (job_id === this.job_id) {
                    this.runLoading = false
                }
            })
        },
        // Once the run is over: which servers' rows are kept
        refreshRun() {
            const job_id = this.job_id
            api.get(job_id).then((run) => {
                if (job_id === this.job_id) {
                    this.run = run
                    this.$store.commit("jobs/setJob", run)
                }
            }).catch(() => {})
        },
        cancel() {
            this.cancelRequested = true
            this.$store.dispatch("jobs/cancel", this.job_id).catch((error) => {
                this.cancelRequested = false
                this.$bvToast.toast(String(error), { title: "Could not cancel the run", variant: "danger", solid: true })
            })
        },
        loadRecent() {
            this.recentLoading = true
            this.recentError = null
            api.recent(10).then((answer) => {
                this.recent = answer.jobs || []
            }).catch((error) => {
                this.recentError = String(error)
            }).finally(() => {
                this.recentLoading = false
            })
        },
    },
}
</script>

<style scoped>
.query-page {
    max-width: 1320px;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 3rem;
}

.q-header {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 0.75rem 1.5rem;
    margin-bottom: 1.1rem;
}

.q-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
    margin: 0;
}

.q-lede {
    color: #5a6270;
    margin: 0.25rem 0 0;
    max-width: 760px;
    font-size: 0.92rem;
}

.q-recent >>> .dropdown-menu {
    width: 26rem;
    max-width: calc(100vw - 2rem);
    max-height: 26rem;
    overflow-y: auto;
}

.q-recent >>> .q-recent-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    white-space: nowrap;
}

.q-recent-note {
    font-size: 0.85rem;
    color: #5a6270;
}

.q-recent-dot {
    flex: none;
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 50%;
    background: var(--job-fill);
}

.q-recent-title {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    font-size: 0.8rem;
}

.q-recent-when {
    flex: none;
    font-size: 0.75rem;
    color: #8a919c;
}

.q-recent >>> .active .q-recent-when {
    color: rgba(255, 255, 255, 0.82);
}

.q-composer {
    padding: 1rem 1.1rem 0.9rem;
    background: #fff;
    border: 1px solid var(--health-rule);
    border-radius: 8px;
    box-shadow: 0 1px 2px rgba(33, 45, 64, 0.04);
}

.q-targets {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem 0.6rem;
    margin-bottom: 0.75rem;
}

.q-targets-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #5a6270;
}

.q-target-button {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.65rem;
    border: 1px solid #cfd5dd;
    border-radius: 6px;
    background: #fff;
    color: var(--var-color-yankeesblue);
    font-weight: 600;
    font-size: 0.9rem;
    transition: border-color 0.12s ease, background-color 0.12s ease;
}

.q-target-button:hover {
    border-color: #a9b3bf;
    background: #f8fafc;
}

.q-target-button:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 2px;
}

.q-chevron {
    font-size: 0.7rem;
    color: #8a919c;
}

.q-stat {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.12rem 0.55rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--job-ink);
    background: var(--job-tint);
}

.q-picker {
    margin-bottom: 0.85rem;
    padding: 0.85rem;
    border-radius: 6px;
    background: #f8f9fb;
    border: 1px solid #eef0f3;
}

.q-footer {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 1rem;
    margin-top: 0.65rem;
}

.q-status {
    display: flex;
    align-items: baseline;
    gap: 0.45rem;
    flex: 1 1 22rem;
    min-width: 0;
    font-size: 0.86rem;
}

.q-status-muted { color: #6b7380; }
.q-status-ok { color: #2f5b3f; }
.q-status-ok i { color: var(--health-ok); }
.q-status-error { color: #8a1f25; }
.q-status-error i { color: var(--health-critical); }

.q-footer-actions {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-left: auto;
}

.q-examples >>> .q-examples-toggle {
    font-size: 0.86rem;
}

/* Quieter than Examples: it takes things away */
.q-clear {
    font-size: 0.86rem;
    color: #5a6270;
}

.q-clear:hover:not(:disabled) {
    color: var(--health-critical-ink);
    text-decoration: none;
}

.q-examples >>> .dropdown-menu {
    width: 30rem;
    max-width: calc(100vw - 2rem);
}

.q-examples >>> .dropdown-item {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    white-space: normal;
    padding-top: 0.45rem;
    padding-bottom: 0.45rem;
}

.q-example-title {
    font-size: 0.86rem;
    font-weight: 600;
}

.q-example-code {
    font-size: 0.76rem;
    color: #5a6270;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.q-run {
    display: inline-flex;
    align-items: center;
    padding-left: 0.9rem;
    padding-right: 0.7rem;
    font-weight: 600;
}

.q-kbd {
    margin-left: 0.6rem;
    padding: 0.05rem 0.35rem;
    border-radius: 3px;
    background: rgba(255, 255, 255, 0.2);
    color: inherit;
    font-size: 0.7rem;
    font-weight: 600;
    box-shadow: none;
}

.q-blocker {
    margin: 0.4rem 0 0;
    text-align: right;
    font-size: 0.8rem;
    color: #6b7380;
}

.q-refused {
    margin-top: 0.75rem;
}

.q-results {
    margin-top: 1.25rem;
}

.q-state {
    padding: 1.5rem 0;
    color: #4a5260;
}

.q-state-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
}

.q-run-header {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.5rem 1rem;
    margin-bottom: 0.6rem;
}

.q-run-heading {
    min-width: 0;
    flex: 1 1 30rem;
}

.q-run-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.86rem;
    color: #5a6270;
}

.q-run-meta .dot {
    color: #b3b9c1;
}

.q-run-status {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.12rem 0.55rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--job-ink);
    background: var(--job-tint);
}

.q-run-statement {
    margin: 0.45rem 0 0;
    padding: 0.4rem 0.6rem;
    max-height: 6.5rem;
    overflow: auto;
    border-radius: 4px;
    background: #f4f6f8;
    border: 1px solid #e6e9ed;
    font-size: 0.8rem;
    color: #3c4452;
    white-space: pre-wrap;
}

.q-run-actions {
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

.q-progress {
    height: 4px;
    margin-bottom: 0.75rem;
    border-radius: 999px;
    background: #e6e9ed;
    overflow: hidden;
}

.q-progress > span {
    display: block;
    height: 100%;
    background: var(--var-color-lapislazuli);
    transition: width 0.3s ease;
}

.q-block {
    margin-top: 1.25rem;
}

.q-block-title {
    margin: 0 0 0.5rem;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #5a6270;
}

.q-note {
    margin: 0 0 0.6rem;
    font-size: 0.85rem;
    color: #5a6270;
}

.q-empty {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
    gap: 1rem;
    margin-top: 1.5rem;
}

.q-empty-item {
    display: flex;
    gap: 0.75rem;
    padding: 0.9rem 1rem;
    border: 1px dashed #d6dbe2;
    border-radius: 8px;
}

.q-empty-item > i {
    flex: none;
    margin-top: 0.15rem;
    font-size: 1.05rem;
    color: var(--var-color-lapislazuli);
}

.q-empty-item strong {
    display: block;
    font-size: 0.9rem;
    color: var(--var-color-yankeesblue);
}

.q-empty-item p {
    margin: 0.2rem 0 0;
    font-size: 0.84rem;
    color: #5a6270;
}
</style>
