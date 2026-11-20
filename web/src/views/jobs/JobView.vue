<template>
<Layout name="LayoutDefault">
    <div class="page-container job-page">
        <div v-if="loading && !job" class="job-state" aria-live="polite">
            <b-spinner small class="mr-2"></b-spinner>Loading the job
        </div>

        <div v-else-if="notFound" class="job-state">
            <h1 class="job-state-title">Job not found</h1>
            <p>It may have been deleted by the retention policy, or it belongs to someone else.</p>
        </div>

        <b-alert v-else-if="error && !job" show variant="danger">
            <strong>Could not load the job.</strong> {{ error }}
            <b-button size="sm" variant="outline-danger" class="ml-2" @click="load">Try again</b-button>
        </b-alert>

        <template v-else-if="job">
            <header class="job-header">
                <div class="job-heading">
                    <div class="job-eyebrow">
                        <span>{{ kindLabel }}</span>
                        <template v-if="job.fleet_name">
                            <span class="dot" aria-hidden="true">·</span>
                            <router-link
                                v-if="job.fleet_id && own"
                                :to="{ name: 'fleet.view', params: { fleet_id: job.fleet_id } }"
                            >{{ job.fleet_name }}</router-link>
                            <span v-else>{{ job.fleet_name }}</span>
                        </template>
                    </div>
                    <h1 class="job-title">{{ job.title }}</h1>
                    <p class="job-meta">
                        <span :title="absolute(job.created)">Created {{ relative(job.created) }}</span>
                        <template v-if="job.user_email">
                            <span class="dot" aria-hidden="true">·</span>
                            <span :class="{ 'is-gone': !job.user_id }">by {{ job.user_email }}<template v-if="!job.user_id"> (deleted user)</template></span>
                        </template>
                    </p>
                    <p v-if="!own" class="job-foreign">
                        <i class="fas fa-user-shield mr-1" aria-hidden="true"></i>
                        You see this job as an admin. You can cancel it, but only the user who started it can run it again.
                    </p>
                </div>
                <div class="job-actions">
                    <b-button
                        v-if="job.kind === 'mispql_query'"
                        size="sm"
                        variant="outline-primary"
                        :to="{ name: 'query', params: { job_id: job.id } }"
                    >
                        <i class="fas fa-magnifying-glass mr-1" aria-hidden="true"></i>Open in Query
                    </b-button>
                    <b-button
                        v-if="!final"
                        size="sm"
                        variant="outline-danger"
                        :disabled="cancelRequested"
                        @click="cancel"
                    >
                        <i class="fas fa-ban mr-1" aria-hidden="true"></i>{{ cancelRequested ? 'Cancelling…' : 'Cancel' }}
                    </b-button>
                    <template v-if="final && own">
                        <b-button
                            v-if="job.failed > 0"
                            size="sm"
                            variant="primary"
                            :disabled="retrying"
                            @click="retry(true)"
                        >
                            <i class="fas fa-redo mr-1" aria-hidden="true"></i>Retry {{ job.failed }} failed server{{ job.failed === 1 ? '' : 's' }}
                        </b-button>
                        <b-button
                            size="sm"
                            :variant="job.failed > 0 ? 'outline-secondary' : 'outline-primary'"
                            :disabled="retrying"
                            @click="retry(false)"
                        >Run again on all</b-button>
                    </template>
                </div>
            </header>

            <section class="job-card" aria-label="Progress">
                <JobProgress :job="job"></JobProgress>
                <p v-if="cancelRequested && !final" class="job-hint">
                    Servers already in progress finish; the others are skipped.
                </p>
            </section>

            <section class="job-card job-params" aria-labelledby="job-params-title">
                <button
                    type="button"
                    class="job-params-toggle"
                    :aria-expanded="paramsOpen ? 'true' : 'false'"
                    aria-controls="job-params-body"
                    @click="paramsOpen = !paramsOpen"
                >
                    <i :class="['fas', paramsOpen ? 'fa-caret-down' : 'fa-caret-right', 'fa-fw']" aria-hidden="true"></i>
                    <span id="job-params-title">Parameters</span>
                    <span class="job-params-summary">{{ paramsSummary }}</span>
                </button>
                <div v-show="paramsOpen" id="job-params-body" class="job-params-body">
                    <jsonViewer :item="job.params" rootKeyName="params" :open="true"></jsonViewer>
                    <p class="job-hint mb-0">Credentials are shown as <code>***</code>: they are kept encrypted, for retries.</p>
                </div>
            </section>

            <section aria-labelledby="job-results-title">
                <h2 id="job-results-title" class="job-section-title">Servers</h2>
                <JobResultsTable :job="job"></JobResultsTable>
            </section>
        </template>
    </div>
</Layout>
</template>

<script>
import moment from "moment"
import Layout from "@/components/layout/Layout.vue"
import JobProgress from "@/components/jobs/JobProgress.vue"
import JobResultsTable from "@/components/jobs/JobResultsTable.vue"
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"
import { JOB_KIND_LABELS, isFinalJob } from "@/helpers/jobs"

const POLL_INTERVAL = 3000

export default {
    name: "JobView",
    components: {
        Layout,
        JobProgress,
        JobResultsTable,
        jsonViewer,
    },
    props: {
        job_id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            loading: false,
            notFound: false,
            error: null,
            cancelRequested: false,
            retrying: false,
            paramsOpen: false,
        }
    },
    computed: {
        job() {
            return this.$store.getters["jobs/job"](this.job_id)
        },
        final() {
            return isFinalJob(this.job)
        },
        // Jobs of other users (an admin's view) get no live events: they go to their owner only
        own() {
            const user = this.$store.getters["auth/user"]
            return !this.job || (user !== null && this.job.user_id === user.id)
        },
        needsPolling() {
            return Boolean(this.job) && !this.final && !this.own
        },
        kindLabel() {
            return JOB_KIND_LABELS[this.job.kind] || this.job.kind
        },
        paramsSummary() {
            const params = this.job.params || {}
            if (params.plugin_id) {
                return params.plugin_id
            }
            if (params.url) {
                return `${params.method || "GET"} ${params.url}`
            }
            if (params.operation) {
                return params.operation.replace(/_/g, " ")
            }
            return ""
        },
    },
    watch: {
        job_id() {
            this.cancelRequested = false
            this.load()
        },
        final(final) {
            if (final) {
                this.cancelRequested = false
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
    mounted() {
        this.load()
    },
    beforeDestroy() {
        clearInterval(this.pollTimer)
    },
    methods: {
        load() {
            this.loading = true
            this.notFound = false
            this.error = null
            this.$store.dispatch("jobs/fetch", this.job_id)
                .catch((error) => {
                    if (String(error).includes("Unknown job")) {
                        this.notFound = true
                    } else {
                        this.error = error
                    }
                })
                .finally(() => {
                    this.loading = false
                })
        },
        relative(timestamp) {
            return timestamp ? moment.unix(timestamp).fromNow() : ""
        },
        absolute(timestamp) {
            return timestamp ? moment.unix(timestamp).format("YYYY-MM-DD HH:mm:ss") : ""
        },
        cancel() {
            this.cancelRequested = true
            this.$store.dispatch("jobs/cancel", this.job_id)
                .catch((error) => {
                    this.cancelRequested = false
                    this.$bvToast.toast(error, { title: "Could not cancel the job", variant: "danger" })
                })
        },
        retry(onlyFailed) {
            this.retrying = true
            this.$store.dispatch("jobs/retry", { job_id: this.job_id, only_failed: onlyFailed })
                .then((job) => {
                    this.$router.push({ name: "jobs.view", params: { job_id: job.id } })
                })
                .catch((error) => {
                    this.$bvToast.toast(error, { title: "Could not start the retry", variant: "danger" })
                })
                .finally(() => {
                    this.retrying = false
                })
        },
    },
}
</script>

<style scoped>
.job-page {
    max-width: 1180px;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 3rem;
}

.job-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
}

.job-heading {
    min-width: 0;
}

.job-eyebrow {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #5a6270;
}

.job-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
    margin: 0.15rem 0 0;
    word-break: break-word;
}

.job-meta {
    color: #5a6270;
    margin: 0.2rem 0 0;
    font-size: 0.9rem;
}

.dot {
    margin: 0 0.35rem;
}

.is-gone {
    font-style: italic;
}

.job-foreign {
    display: inline-block;
    margin: 0.5rem 0 0;
    padding: 0.3rem 0.7rem;
    border-radius: 4px;
    font-size: 0.82rem;
    color: var(--health-info-ink);
    background: var(--health-info-tint);
}

.job-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.job-card {
    background: #fff;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
}

.job-hint {
    margin: 0.6rem 0 0;
    font-size: 0.82rem;
    color: #6c757d;
}

.job-params {
    padding: 0;
}

.job-params-toggle {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    width: 100%;
    padding: 0.75rem 1.25rem;
    border: none;
    background: none;
    text-align: left;
    font-weight: 600;
    color: var(--var-color-yankeesblue);
}

.job-params-toggle:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: -2px;
}

.job-params-summary {
    font-weight: 400;
    color: #6c757d;
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.82rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.job-params-body {
    padding: 0 1.25rem 1rem;
    font-size: 0.85rem;
}

.job-section-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
    margin: 1.25rem 0 0.5rem;
}

.job-state {
    padding: 3rem 1rem;
    text-align: center;
    color: #5a6270;
}

.job-state-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
}
</style>
