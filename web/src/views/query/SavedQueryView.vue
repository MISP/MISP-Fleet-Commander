<template>
<Layout name="LayoutDefault">
    <div class="page-container saved-view">
        <div v-if="loading && !saved" class="sv-state" role="status">
            <b-spinner small class="mr-2"></b-spinner>Loading the saved query…
        </div>
        <div v-else-if="notFound" class="sv-state">
            <h1 class="sv-state-title">Saved query not found</h1>
            <p>It may have been deleted. <router-link :to="{ name: 'query.saved' }">Your saved queries</router-link></p>
        </div>
        <b-alert v-else-if="error && !saved" show variant="danger">
            Could not load the saved query: {{ error }}
            <b-button size="sm" variant="outline-danger" class="ml-2" @click="load">Try again</b-button>
        </b-alert>

        <template v-else-if="saved">
            <header class="sv-header">
                <div class="sv-heading">
                    <h1 class="sv-title">{{ saved.name }}</h1>
                    <p v-if="saved.description" class="sv-lede">{{ saved.description }}</p>
                </div>
                <div class="sv-actions">
                    <b-button
                        variant="primary"
                        size="sm"
                        :disabled="running || starting || saved.server_count === 0"
                        :title="saved.server_count === 0 ? saved.last_error : 'Run it now on its servers'"
                        @click="run"
                    >
                        <b-spinner v-if="running || starting" small class="mr-1"></b-spinner>
                        <i v-else class="fas fa-play mr-1" aria-hidden="true"></i>{{ running ? 'Running…' : 'Run now' }}
                    </b-button>
                    <b-button variant="outline-secondary" size="sm" :to="{ name: 'query', query: { saved: String(saved.id) } }">
                        <i class="fas fa-magnifying-glass mr-1" aria-hidden="true"></i>Open in Query
                    </b-button>
                    <b-button variant="outline-secondary" size="sm" @click="$bvModal.show('sv-edit')">
                        <i class="fas fa-pen mr-1" aria-hidden="true"></i>Edit…
                    </b-button>
                    <b-button variant="link" size="sm" class="sv-delete" @click="remove">Delete</b-button>
                </div>
            </header>

            <b-alert v-if="saved.statement_error" show variant="danger" class="sv-alert">
                <strong>The statement no longer passes the checks:</strong> {{ saved.statement_error.message }}.
                Scheduled runs report it as invalid on every server; open it in Query to fix it.
            </b-alert>
            <b-alert v-else-if="saved.last_error" show variant="warning" class="sv-alert">
                <i class="fas fa-triangle-exclamation mr-1" aria-hidden="true"></i>{{ saved.last_error }}.
                <template v-if="saved.server_count === 0">
                    <router-link :to="{ name: 'query', query: { saved: String(saved.id) } }">Open it in Query</router-link> to choose its servers.
                </template>
            </b-alert>
            <b-alert v-if="saved.schedule_minutes && options && options.scheduled_runs === false" show variant="warning" class="sv-alert">
                <i class="fas fa-pause mr-1" aria-hidden="true"></i>
                Scheduled runs are turned off in the settings (Queries): it only runs by hand until they are on.
            </b-alert>

            <dl class="sv-facts">
                <div class="sv-fact">
                    <dt>Runs on</dt>
                    <dd>
                        {{ targetText(saved) }}
                        <span class="sv-fact-note">{{ targetNote }}</span>
                    </dd>
                </div>
                <div class="sv-fact">
                    <dt>Schedule</dt>
                    <dd>
                        {{ scheduleText }}
                        <span v-if="nextText" class="sv-fact-note">Next run {{ nextText }}</span>
                    </dd>
                </div>
                <div class="sv-fact">
                    <dt>Each server should</dt>
                    <dd>
                        <template v-if="saved.expectation_text">
                            {{ expectationSentence }}
                            <span :class="['sv-severity', `sev-${saved.severity}`]">
                                <i :class="severityMeta.icon" aria-hidden="true"></i>{{ severityMeta.label }} otherwise
                            </span>
                        </template>
                        <template v-else>
                            Anything
                            <span class="sv-fact-note">Answers are kept; no issue is raised</span>
                        </template>
                    </dd>
                </div>
                <div class="sv-fact">
                    <dt>Last run</dt>
                    <dd>
                        <template v-if="saved.last_run_at">
                            <router-link
                                v-if="saved.last_job_id"
                                :to="{ name: 'query', params: { job_id: saved.last_job_id }, query: { saved: String(saved.id) } }"
                                :title="absolute(saved.last_run_at)"
                            >{{ relative(saved.last_run_at) }}</router-link>
                            <span v-else :title="absolute(saved.last_run_at)">{{ relative(saved.last_run_at) }}</span>
                            <span v-if="saved.last_job_status" :class="['sv-job', `job-tone-${jobMeta.tone}`]">{{ jobMeta.label }}</span>
                        </template>
                        <template v-else>Never</template>
                    </dd>
                </div>
            </dl>

            <pre class="sv-statement" aria-label="Statement">{{ saved.statement }}</pre>

            <section class="sv-servers" aria-labelledby="sv-servers-title">
                <div class="sv-servers-head">
                    <h2 id="sv-servers-title" class="sv-block-title">Each server's last answer</h2>
                    <div class="sv-chips">
                        <span v-for="part in parts" :key="part.state" :class="['sv-chip', `job-tone-${part.tone}`]">
                            <i :class="['fas', part.icon]" aria-hidden="true"></i>{{ part.text }}
                        </span>
                    </div>
                </div>
                <p v-if="!saved.servers.length" class="sv-note">It runs on no server now.</p>
                <div v-else class="sv-table-wrap">
                    <table class="sv-table">
                        <thead>
                            <tr>
                                <th scope="col">Server</th>
                                <th scope="col">State</th>
                                <th scope="col">Answer</th>
                                <th scope="col" class="sv-col-when">Checked</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="entry in servers" :key="entry.server_id" :class="`job-tone-${entry.meta.tone}`">
                                <td class="sv-server">
                                    <router-link :to="{ name: 'servers.view', params: { server_id: entry.server_id } }">{{ entry.server_name }}</router-link>
                                </td>
                                <td>
                                    <span class="sv-state-badge">
                                        <i :class="['fas', entry.meta.icon]" aria-hidden="true"></i>{{ entry.meta.label }}
                                    </span>
                                </td>
                                <td :class="['sv-answer', { 'sv-answer-number': isNumber(entry) }]">{{ answer(entry) }}</td>
                                <td class="sv-col-when">
                                    <template v-if="entry.result">
                                        <router-link
                                            v-if="entry.result.job_id"
                                            :to="{ name: 'query', params: { job_id: entry.result.job_id }, query: { saved: String(saved.id) } }"
                                            :title="absolute(entry.result.checked_at)"
                                        >{{ relative(entry.result.checked_at) }}</router-link>
                                        <span v-else :title="absolute(entry.result.checked_at)">{{ relative(entry.result.checked_at) }}</span>
                                    </template>
                                    <span v-else class="sv-muted">—</span>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </section>

            <SavedQueryHistory
                v-if="hasHistory"
                :saved-id="saved.id"
                :severity="saved.severity"
                :states="servers"
            ></SavedQueryHistory>

            <SaveQueryModal
                modal-id="sv-edit"
                mode="update"
                :saved="saved"
                :kind="saved.kind"
                :options="options"
                @saved="onEdited"
            ></SaveQueryModal>
        </template>
    </div>
</Layout>
</template>

<script>
import moment from "moment"
import Layout from "@/components/layout/Layout.vue"
import SaveQueryModal from "@/components/query/SaveQueryModal.vue"
import SavedQueryHistory from "@/components/query/SavedQueryHistory.vue"
import api from "@/api/queries"
import { jobStatusMeta } from "@/helpers/jobs"
import { SEVERITY_META } from "@/views/attention/healthLabels"
import {
    CHECKED_KINDS, answerText, overviewParts, runStartedText, scheduleLabel, serversWorstFirst, targetText,
} from "@/helpers/savedQueries"

const POLL_INTERVAL = 3000
const RELOAD_DELAY = 400

// One saved query: what it runs, where, when, what it expects, what each of its servers last answered, and how
// their answers moved over time
export default {
    name: "SavedQueryView",
    components: { Layout, SaveQueryModal, SavedQueryHistory },
    props: {
        saved_id: { type: Number, required: true },
    },
    data() {
        return {
            saved: null,
            loading: false,
            notFound: false,
            error: null,
            options: null,
            starting: false,
        }
    },
    computed: {
        running() {
            return Boolean(this.saved && this.saved.running)
        },
        // A SELECT or a COUNT answers a number, kept over time
        hasHistory() {
            return CHECKED_KINDS.includes(this.saved.kind)
        },
        targetNote() {
            const saved = this.saved
            const servers = `${saved.server_count} server${saved.server_count === 1 ? "" : "s"}`
            const fleets = saved.fleets || []
            if (fleets.length > 0) {
                const names = fleets.length > 1 ? `: ${fleets.map(fleet => fleet.name).join(", ")}` : ""
                return `Follows ${fleets.length === 1 ? "the fleet" : `${fleets.length} fleets`}${names} · ${servers} now`
            }
            const listed = (saved.server_ids || []).length
            if (listed === 0) {
                return ""
            }
            return listed === saved.server_count ? "As chosen" : `${listed - saved.server_count} of those chosen no longer exist`
        },
        scheduleText() {
            return scheduleLabel(this.saved.schedule_minutes, this.options && this.options.schedules)
        },
        nextText() {
            const next = this.saved.next_run_at
            if (!next || this.saved.server_count === 0) {
                return ""
            }
            return next <= Date.now() / 1000 + 60 ? "within a minute" : moment.unix(next).fromNow()
        },
        expectationSentence() {
            const text = this.saved.expectation_text
            if (this.saved.kind === "count") {
                return `Count ${text}`
            }
            return text === "no rows" ? "Find no rows" : "Find some rows"
        },
        severityMeta() {
            return SEVERITY_META[this.saved.severity] || SEVERITY_META.warning
        },
        jobMeta() {
            return jobStatusMeta(this.saved.last_job_status)
        },
        parts() {
            return overviewParts(this.saved.overview, this.saved.severity)
        },
        // Worst first, then by name
        servers() {
            return serversWorstFirst(this.saved.servers, this.saved.severity)
        },
    },
    watch: {
        saved_id() {
            this.saved = null
            this.load()
        },
        running: {
            handler(running) {
                clearInterval(this.pollTimer)
                if (running) {
                    this.pollTimer = setInterval(this.load, POLL_INTERVAL)
                }
            },
        },
    },
    created() {
        this.load()
        api.language().then((language) => { this.options = language.saved || null }).catch(() => {})
        this.unsubscribe = this.$store.subscribeAction({ after: this.onJobEvent })
    },
    beforeDestroy() {
        clearInterval(this.pollTimer)
        clearTimeout(this.reloadTimer)
        if (this.unsubscribe) {
            this.unsubscribe()
        }
    },
    methods: {
        // A run starting anywhere (the schedule, another tab), or a query run ending: its answers are kept by then
        onJobEvent(action) {
            const payload = action.payload || {}
            if (action.type === "jobs/SOCKET_CONNECT" || action.type === "jobs/SOCKET_JOB_STARTED"
                || (action.type === "jobs/SOCKET_JOB_DONE" && payload.kind === "mispql_query")) {
                clearTimeout(this.reloadTimer)
                this.reloadTimer = setTimeout(this.load, RELOAD_DELAY)
            }
        },
        load() {
            const id = this.saved_id
            this.loading = true
            return api.savedGet(id).then((saved) => {
                if (id === this.saved_id) {
                    this.saved = saved
                    this.error = null
                    this.notFound = false
                }
            }).catch((error) => {
                if (id !== this.saved_id) {
                    return
                }
                if (/unknown saved query/i.test(String(error))) {
                    this.notFound = true
                    this.saved = null
                } else {
                    this.error = String(error)
                }
            }).finally(() => {
                this.loading = false
            })
        },
        targetText,
        answer(entry) {
            return entry.result ? answerText(entry.result) : "Not asked yet"
        },
        isNumber(entry) {
            return Boolean(entry.result) && entry.result.outcome === "count"
        },
        relative(timestamp) {
            return moment.unix(timestamp).fromNow()
        },
        absolute(timestamp) {
            return moment.unix(timestamp).format("YYYY-MM-DD HH:mm:ss")
        },
        run() {
            this.starting = true
            api.savedRun(this.saved.id).then((answer) => {
                if (!answer.ok) {
                    this.$bvToast.toast(answer.message || "It cannot run now", { title: "Not run", variant: "danger", solid: true })
                    return
                }
                this.$bvToast.toast(runStartedText(this.saved, answer.job), {
                    title: "Running", variant: "info", solid: true,
                    to: { name: "query", params: { job_id: answer.job_id }, query: { saved: String(this.saved.id) } },
                })
                return this.load()
            }).catch((error) => {
                this.$bvToast.toast(String(error), { title: "Could not run it", variant: "danger", solid: true })
            }).finally(() => {
                this.starting = false
            })
        },
        onEdited(saved) {
            this.saved = saved
        },
        remove() {
            const saved = this.saved
            this.$bvModal.msgBoxConfirm(
                `Delete “${saved.name}”? Its issues on Needs attention go with it; its runs stay on the Jobs page.`,
                { title: "Delete this saved query?", okTitle: "Delete", okVariant: "danger", cancelVariant: "outline-secondary", centered: true },
            ).then((confirmed) => {
                if (!confirmed) {
                    return null
                }
                return api.savedDelete(saved.id).then(() => {
                    this.$router.push({ name: "query.saved" }).catch(() => {})
                })
            }).catch((error) => {
                this.$bvToast.toast(String(error), { title: "Could not delete it", variant: "danger", solid: true })
            })
        },
    },
}
</script>

<style scoped>
.saved-view {
    max-width: 1100px;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 3rem;
}

.sv-state {
    padding: 1.5rem 0;
    color: #4a5260;
}

.sv-state-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
}

.sv-header {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.75rem 1.5rem;
    margin-bottom: 1rem;
}

.sv-heading {
    min-width: 0;
    flex: 1 1 24rem;
}

.sv-title {
    margin: 0;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
    overflow-wrap: anywhere;
}

.sv-lede {
    margin: 0.25rem 0 0;
    max-width: 760px;
    font-size: 0.92rem;
    color: #5a6270;
}

.sv-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
}

.sv-delete {
    color: #5f6873;
}

.sv-delete:hover {
    color: var(--health-critical-ink);
    text-decoration: none;
}

.sv-alert {
    font-size: 0.88rem;
}

.sv-facts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
    gap: 0;
    margin: 0 0 0.85rem;
    border: 1px solid var(--health-rule);
    border-radius: 8px;
    background: #fff;
    box-shadow: 0 1px 2px rgba(33, 45, 64, 0.04);
    overflow: hidden;
}

.sv-fact {
    padding: 0.7rem 0.95rem;
    border-left: 1px solid var(--health-rule);
    margin-left: -1px;
}

.sv-fact dt {
    margin-bottom: 0.2rem;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #5a6270;
}

.sv-fact dd {
    margin: 0;
    font-size: 0.92rem;
    font-weight: 600;
    color: var(--var-color-yankeesblue);
}

.sv-fact-note {
    display: block;
    font-size: 0.8rem;
    font-weight: 400;
    color: #5f6873;
}

.sv-severity {
    display: block;
    margin-top: 0.1rem;
    font-size: 0.8rem;
    font-weight: 600;
}

.sv-severity i {
    margin-right: 0.3rem;
}

.sv-severity.sev-critical { color: var(--health-critical-ink); }
.sv-severity.sev-warning { color: var(--health-warning-ink); }
.sv-severity.sev-info { color: var(--health-info-ink); }

.sv-job {
    margin-left: 0.4rem;
    padding: 0.08rem 0.5rem;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 700;
    color: var(--job-ink);
    background: var(--job-tint);
}

.sv-statement {
    margin: 0 0 1.25rem;
    padding: 0.6rem 0.8rem;
    max-height: 12rem;
    overflow: auto;
    border-radius: 6px;
    background: #f4f6f8;
    border: 1px solid #e6e9ed;
    font-size: 0.84rem;
    color: #3c4452;
    white-space: pre-wrap;
    word-break: break-word;
}

.sv-servers-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.4rem 1rem;
    margin-bottom: 0.5rem;
}

.sv-block-title {
    margin: 0;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #5a6270;
}

.sv-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
}

.sv-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.1rem 0.55rem;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 600;
    color: var(--job-ink);
    background: var(--job-tint);
}

.sv-note {
    font-size: 0.88rem;
    color: #5a6270;
}

.sv-table-wrap {
    overflow-x: auto;
    border: 1px solid var(--health-rule);
    border-radius: 8px;
    background: #fff;
}

.sv-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
}

.sv-table th {
    padding: 0.5rem 0.85rem;
    border-bottom: 1px solid var(--health-rule);
    background: #f8f9fb;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #5a6270;
    text-align: left;
    white-space: nowrap;
}

.sv-table td {
    padding: 0.5rem 0.85rem;
    border-top: 1px solid #eef0f3;
    vertical-align: top;
}

.sv-table tbody tr:first-child td {
    border-top: none;
}

.sv-server {
    font-weight: 600;
    white-space: nowrap;
}

.sv-state-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.08rem 0.55rem;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 700;
    white-space: nowrap;
    color: var(--job-ink);
    background: var(--job-tint);
}

.sv-answer {
    color: #3c4452;
    overflow-wrap: anywhere;
}

.sv-answer-number {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
}

.sv-col-when {
    white-space: nowrap;
    color: #5f6873;
}

.sv-muted {
    color: #9aa1a7;
}

/* Phones: each server as a small card, its answer and time under its name and state */
@media (max-width: 575.98px) {
    .sv-table thead {
        display: none;
    }

    .sv-table,
    .sv-table tbody {
        display: block;
    }

    .sv-table tr {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 0.25rem 0.5rem;
        padding: 0.6rem 0.75rem;
        border-top: 1px solid #eef0f3;
    }

    .sv-table tbody tr:first-child {
        border-top: none;
    }

    .sv-table td {
        padding: 0;
        border: none;
    }

    .sv-table td.sv-answer,
    .sv-table td.sv-col-when {
        grid-column: 1 / -1;
    }

    .sv-table td.sv-col-when {
        font-size: 0.8rem;
    }
}
</style>
