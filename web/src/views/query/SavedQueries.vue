<template>
<Layout name="LayoutDefault">
    <div class="page-container saved-page">
        <header class="sp-header">
            <div>
                <h1 class="sp-title">Saved queries</h1>
                <p class="sp-lede">
                    Statements kept with the servers they run on. On a schedule and with an expectation, each server
                    whose answer is not as expected shows on Needs attention.
                </p>
            </div>
            <b-button variant="outline-primary" size="sm" :to="{ name: 'query' }">
                <i class="fas fa-plus mr-1" aria-hidden="true"></i>New query
            </b-button>
        </header>

        <b-alert v-if="options && options.scheduled_runs === false" show variant="warning" class="sp-alert">
            <i class="fas fa-pause mr-1" aria-hidden="true"></i>
            Scheduled runs are turned off in the settings (Queries): saved queries only run by hand.
        </b-alert>

        <div v-if="loading && saved.length === 0" class="sp-state" role="status">
            <b-spinner small class="mr-2"></b-spinner>Loading your saved queries…
        </div>
        <b-alert v-else-if="error && saved.length === 0" show variant="danger">
            Could not load your saved queries: {{ error }}
            <b-button size="sm" variant="outline-danger" class="ml-2" @click="load">Try again</b-button>
        </b-alert>
        <section v-else-if="saved.length === 0" class="sp-empty">
            <i class="fas fa-bookmark sp-empty-icon" aria-hidden="true"></i>
            <h2 class="sp-empty-title">No saved query yet</h2>
            <p>
                Write a statement on the Query page, choose its servers, then press <strong>Save</strong>. Keep it
                to run again, run it every hour or every day, and say what each server should answer: for example
                that no server holds an indicator, or that a feed still brings events.
            </p>
            <b-button variant="primary" :to="{ name: 'query' }">
                <i class="fas fa-magnifying-glass mr-1" aria-hidden="true"></i>Write a query
            </b-button>
        </section>

        <template v-else>
            <div class="sp-toolbar">
                <b-form-input
                    v-if="saved.length > 5"
                    v-model="filter"
                    type="search"
                    size="sm"
                    class="sp-filter"
                    placeholder="Filter by name, statement or description"
                    aria-label="Filter saved queries"
                ></b-form-input>
                <span class="sp-count">{{ countText }}</span>
            </div>
            <p v-if="shown.length === 0" class="sp-state">No saved query matches “{{ filter }}”.</p>
            <ul class="sp-list">
                <li v-for="entry in shown" :key="entry.id" :class="['sp-item', `job-tone-${worstTone(entry)}`]">
                    <div class="sp-item-main">
                        <router-link :to="viewLink(entry)" class="sp-item-name">{{ entry.name }}</router-link>
                        <p v-if="entry.description" class="sp-item-description">{{ entry.description }}</p>
                        <code class="sp-item-statement" :title="entry.statement">{{ oneLine(entry.statement) }}</code>
                        <div class="sp-facts">
                            <span :class="{ 'sp-fact-missing': entry.server_count === 0 }">
                                <i class="fas fa-server" aria-hidden="true"></i>{{ targetText(entry) }}
                            </span>
                            <span>
                                <i class="fas fa-clock" aria-hidden="true"></i>{{ scheduleText(entry) }}
                            </span>
                            <span v-if="entry.expectation_text">
                                <i class="fas fa-bullseye" aria-hidden="true"></i>Expects {{ entry.expectation_text }}
                            </span>
                            <span v-if="entry.expectation_text && entry.schedule_minutes" :class="['sp-severity', `sev-${entry.severity}`]">
                                <i :class="severityMeta(entry.severity).icon" aria-hidden="true"></i>{{ severityMeta(entry.severity).label }}
                            </span>
                        </div>
                    </div>
                    <div class="sp-item-status">
                        <div v-if="entry.running || starting[entry.id]" class="sp-chip job-tone-running">
                            <i class="fas fa-spinner fa-spin" aria-hidden="true"></i>Running
                        </div>
                        <div v-else-if="parts(entry).length" class="sp-chips">
                            <span v-for="part in parts(entry)" :key="part.state" :class="['sp-chip', `job-tone-${part.tone}`]">
                                <i :class="['fas', part.icon]" aria-hidden="true"></i>{{ part.text }}
                            </span>
                        </div>
                        <div class="sp-when">
                            <template v-if="entry.last_run_at">
                                Last run
                                <router-link
                                    v-if="entry.last_job_id"
                                    :to="{ name: 'query', params: { job_id: entry.last_job_id } }"
                                    :title="absolute(entry.last_run_at)"
                                >{{ relative(entry.last_run_at) }}</router-link>
                                <span v-else :title="absolute(entry.last_run_at)">{{ relative(entry.last_run_at) }}</span>
                            </template>
                            <template v-else>Never run</template>
                            <template v-if="entry.next_run_at && entry.server_count > 0">
                                <span class="dot" aria-hidden="true">·</span>
                                next {{ nextText(entry.next_run_at) }}
                            </template>
                        </div>
                        <p v-if="entry.last_error" class="sp-item-error">
                            <i class="fas fa-triangle-exclamation" aria-hidden="true"></i>{{ entry.last_error }}
                        </p>
                    </div>
                    <div class="sp-item-actions">
                        <b-button
                            size="sm"
                            variant="outline-primary"
                            :disabled="entry.running || Boolean(starting[entry.id]) || entry.server_count === 0"
                            :title="entry.server_count === 0 ? entry.last_error : 'Run it now on its servers'"
                            @click="run(entry)"
                        >
                            <i class="fas fa-play mr-1" aria-hidden="true"></i>Run now
                        </b-button>
                        <b-dropdown size="sm" variant="link" right no-caret toggle-class="sp-more" :aria-label="`More for ${entry.name}`">
                            <template #button-content>
                                <i class="fas fa-ellipsis" aria-hidden="true"></i><span class="sr-only">More</span>
                            </template>
                            <b-dropdown-item :to="{ name: 'query', query: { saved: String(entry.id) } }">
                                <i class="fas fa-magnifying-glass fa-fw mr-1" aria-hidden="true"></i>Open in Query
                            </b-dropdown-item>
                            <b-dropdown-item-button @click="edit(entry)">
                                <i class="fas fa-pen fa-fw mr-1" aria-hidden="true"></i>Edit details…
                            </b-dropdown-item-button>
                            <b-dropdown-divider></b-dropdown-divider>
                            <b-dropdown-item-button variant="danger" @click="remove(entry)">
                                <i class="fas fa-trash fa-fw mr-1" aria-hidden="true"></i>Delete…
                            </b-dropdown-item-button>
                        </b-dropdown>
                    </div>
                </li>
            </ul>
        </template>

        <SaveQueryModal
            v-if="editing"
            modal-id="sp-edit"
            mode="update"
            :saved="editing"
            :kind="editing ? editing.kind : null"
            :options="options"
            @saved="onEdited"
        ></SaveQueryModal>
    </div>
</Layout>
</template>

<script>
import moment from "moment"
import Layout from "@/components/layout/Layout.vue"
import SaveQueryModal from "@/components/query/SaveQueryModal.vue"
import api from "@/api/queries"
import { SEVERITY_META } from "@/views/attention/healthLabels"
import { overviewParts, runStartedText, scheduleLabel, targetText } from "@/helpers/savedQueries"

const POLL_INTERVAL = 3000
const RELOAD_DELAY = 400

// The user's saved queries: what each runs, where and when, and how its servers last answered
export default {
    name: "SavedQueries",
    components: { Layout, SaveQueryModal },
    data() {
        return {
            saved: [],
            loading: false,
            error: null,
            options: null,
            filter: "",
            starting: {},
            editing: null,
        }
    },
    computed: {
        shown() {
            const words = this.filter.trim().toLowerCase().split(/\s+/).filter(Boolean)
            if (!words.length) {
                return this.saved
            }
            return this.saved.filter((entry) => {
                const text = `${entry.name} ${entry.description} ${entry.statement}`.toLowerCase()
                return words.every(word => text.includes(word))
            })
        },
        countText() {
            const total = this.saved.length
            const scheduled = this.saved.filter(entry => entry.schedule_minutes).length
            return `${total} saved quer${total === 1 ? "y" : "ies"}, ${scheduled} on a schedule`
        },
        anyRunning() {
            return this.saved.some(entry => entry.running)
        },
    },
    watch: {
        anyRunning: {
            handler(running) {
                clearInterval(this.pollTimer)
                if (running) {
                    this.pollTimer = setInterval(this.load, POLL_INTERVAL)
                }
            },
            immediate: true,
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
            this.loading = true
            return api.savedList().then((answer) => {
                this.saved = answer.saved || []
                this.error = null
            }).catch((error) => {
                this.error = String(error)
            }).finally(() => {
                this.loading = false
            })
        },
        viewLink(entry) {
            return { name: "query.saved.view", params: { saved_id: String(entry.id) } }
        },
        oneLine(text) {
            return text.replace(/\s+/g, " ").trim()
        },
        targetText,
        scheduleText(entry) {
            return scheduleLabel(entry.schedule_minutes, this.options && this.options.schedules)
        },
        severityMeta(severity) {
            return SEVERITY_META[severity] || SEVERITY_META.warning
        },
        parts(entry) {
            return overviewParts(entry.overview, entry.severity)
        },
        worstTone(entry) {
            const [worst] = this.parts(entry)
            return worst && worst.state !== "met" && worst.state !== "answered" && worst.state !== "not_run" ? worst.tone : "none"
        },
        relative(timestamp) {
            return moment.unix(timestamp).fromNow()
        },
        absolute(timestamp) {
            return moment.unix(timestamp).format("YYYY-MM-DD HH:mm:ss")
        },
        nextText(timestamp) {
            return timestamp <= Date.now() / 1000 + 60 ? "within a minute" : moment.unix(timestamp).fromNow()
        },
        run(entry) {
            this.$set(this.starting, entry.id, true)
            api.savedRun(entry.id).then((answer) => {
                if (!answer.ok) {
                    this.$bvToast.toast(answer.message || "It cannot run now", { title: `Not run: ${entry.name}`, variant: "danger", solid: true })
                    return
                }
                this.$bvToast.toast(runStartedText(entry, answer.job), {
                    title: "Running", variant: "info", solid: true, to: { name: "query", params: { job_id: answer.job_id } },
                })
                return this.load()
            }).catch((error) => {
                this.$bvToast.toast(String(error), { title: `Could not run ${entry.name}`, variant: "danger", solid: true })
            }).finally(() => {
                this.$delete(this.starting, entry.id)
            })
        },
        edit(entry) {
            this.editing = entry
            this.$nextTick(() => this.$bvModal.show("sp-edit"))
        },
        onEdited() {
            this.load()
        },
        remove(entry) {
            this.$bvModal.msgBoxConfirm(
                `Delete “${entry.name}”? Its issues on Needs attention go with it; its runs stay on the Jobs page.`,
                { title: "Delete this saved query?", okTitle: "Delete", okVariant: "danger", cancelVariant: "outline-secondary", centered: true },
            ).then((confirmed) => {
                if (!confirmed) {
                    return null
                }
                return api.savedDelete(entry.id).then(() => this.load())
            }).catch((error) => {
                this.$bvToast.toast(String(error), { title: "Could not delete it", variant: "danger", solid: true })
            })
        },
    },
}
</script>

<style scoped>
.saved-page {
    max-width: 1320px;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 3rem;
}

.sp-header {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 0.75rem 1.5rem;
    margin-bottom: 1.1rem;
}

.sp-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
    margin: 0;
}

.sp-lede {
    color: #5a6270;
    margin: 0.25rem 0 0;
    max-width: 760px;
    font-size: 0.92rem;
}

.sp-alert {
    font-size: 0.88rem;
}

.sp-state {
    padding: 1.25rem 0;
    color: #4a5260;
}

.sp-empty {
    max-width: 640px;
    margin: 2rem auto;
    padding: 2rem 1.5rem;
    text-align: center;
    border: 1px dashed #d6dbe2;
    border-radius: 8px;
    color: #4a5260;
}

.sp-empty-icon {
    font-size: 1.6rem;
    color: var(--var-color-lapislazuli);
}

.sp-empty-title {
    margin: 0.6rem 0 0.4rem;
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
}

.sp-empty p {
    font-size: 0.9rem;
}

.sp-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 1rem;
    margin-bottom: 0.6rem;
}

.sp-filter {
    flex: 0 1 22rem;
}

.sp-count {
    margin-left: auto;
    font-size: 0.82rem;
    color: #5f6873;
}

.sp-list {
    margin: 0;
    padding: 0;
    list-style: none;
    border: 1px solid var(--health-rule);
    border-radius: 8px;
    background: #fff;
    box-shadow: 0 1px 2px rgba(33, 45, 64, 0.04);
}

.sp-item {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(14rem, 20rem) auto;
    gap: 0.5rem 1.25rem;
    align-items: start;
    padding: 0.85rem 1rem 0.85rem 1.1rem;
    border-top: 1px solid var(--health-rule);
    /* A bar on the left in the tone of the worst state, when one deserves attention */
    box-shadow: inset 3px 0 0 var(--job-fill, transparent);
}

.sp-item:first-child {
    border-top: none;
    border-radius: 8px 8px 0 0;
}

.sp-item:last-child {
    border-radius: 0 0 8px 8px;
}

.sp-item.job-tone-none {
    --job-fill: transparent;
}

.sp-item-main {
    min-width: 0;
}

.sp-item-name {
    font-weight: 700;
    font-size: 0.98rem;
    color: var(--var-color-yankeesblue);
}

.sp-item-description {
    margin: 0.1rem 0 0;
    font-size: 0.86rem;
    color: #4a5260;
}

.sp-item-statement {
    display: block;
    margin-top: 0.3rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.78rem;
    color: #3c4452;
}

.sp-facts {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem 1rem;
    margin-top: 0.4rem;
    font-size: 0.8rem;
    color: #5a6270;
}

.sp-facts i {
    margin-right: 0.35rem;
    color: #8a919c;
}

.sp-fact-missing {
    color: var(--health-warning-ink);
}

.sp-severity {
    font-weight: 600;
}

.sp-severity.sev-critical,
.sp-severity.sev-critical i {
    color: var(--health-critical-ink);
}

.sp-severity.sev-warning,
.sp-severity.sev-warning i {
    color: var(--health-warning-ink);
}

.sp-severity.sev-info,
.sp-severity.sev-info i {
    color: var(--health-info-ink);
}

.sp-item-status {
    min-width: 0;
}

.sp-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
}

.sp-chip {
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

.sp-when {
    margin-top: 0.35rem;
    font-size: 0.8rem;
    color: #5f6873;
}

.sp-when .dot {
    margin: 0 0.25rem;
    color: #b3b9c1;
}

.sp-item-error {
    margin: 0.3rem 0 0;
    font-size: 0.8rem;
    color: var(--health-warning-ink);
}

.sp-item-error i {
    margin-right: 0.3rem;
}

.sp-item-actions {
    display: flex;
    align-items: center;
    gap: 0.15rem;
}

.sp-item-actions >>> .sp-more {
    color: #5f6873;
    padding-left: 0.5rem;
    padding-right: 0.5rem;
}

.sp-item-actions >>> .sp-more:hover {
    color: var(--var-color-yankeesblue);
}

@media (max-width: 991.98px) {
    .sp-item {
        grid-template-columns: minmax(0, 1fr) auto;
    }

    .sp-item-status {
        grid-column: 1;
        grid-row: 2;
    }

    .sp-item-actions {
        grid-column: 2;
        grid-row: 1 / span 2;
    }
}

@media (max-width: 575.98px) {
    .sp-item {
        grid-template-columns: minmax(0, 1fr);
    }

    .sp-item-status,
    .sp-item-actions {
        grid-column: 1;
        grid-row: auto;
    }
}
</style>
