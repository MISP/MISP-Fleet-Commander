<template>
    <section class="job-run" :aria-label="job ? 'Job progress' : 'Selected servers'">
        <div class="job-run-head">
            <JobProgress v-if="job" :job="job" class="job-run-progress"></JobProgress>
            <div v-else class="job-run-idle">
                <strong>{{ servers.length }}</strong> selected server{{ servers.length === 1 ? '' : 's' }}
                <span class="job-run-idle-hint">Results appear here as each server answers. You can close this window: the job keeps running and you are notified when it ends.</span>
            </div>
            <div v-if="job" class="job-run-actions">
                <b-button
                    v-if="!final"
                    size="sm"
                    variant="outline-danger"
                    :disabled="cancelRequested"
                    @click="cancel"
                >{{ cancelRequested ? 'Cancelling…' : 'Cancel' }}</b-button>
                <b-button
                    v-if="final && job.failed > 0"
                    size="sm"
                    variant="primary"
                    :disabled="retrying"
                    @click="retryFailed"
                ><i class="fas fa-redo mr-1" aria-hidden="true"></i>Retry {{ job.failed }} failed server{{ job.failed === 1 ? '' : 's' }}</b-button>
                <b-button
                    size="sm"
                    variant="link"
                    class="job-run-link"
                    :to="{ name: 'jobs.view', params: { job_id: job.id } }"
                    @click="$emit('navigate')"
                >Job page<i class="fas fa-arrow-right ml-1" aria-hidden="true"></i></b-button>
            </div>
        </div>
        <JobResultsTable
            :job="job"
            :servers="servers"
            max-height="320px"
            @navigate="$emit('navigate')"
        ></JobResultsTable>
    </section>
</template>

<script>
import JobProgress from "@/components/jobs/JobProgress.vue"
import JobResultsTable from "@/components/jobs/JobResultsTable.vue"
import { isFinalJob } from "@/helpers/jobs"

// A job started from a batch modal: its progress, Cancel / Retry, and the per-server results
export default {
    name: "JobRunPanel",
    components: {
        JobProgress,
        JobResultsTable,
    },
    props: {
        job: {
            type: Object,
            default: null,
        },
        servers: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            cancelRequested: false,
            retrying: false,
        }
    },
    computed: {
        final() {
            return isFinalJob(this.job)
        },
    },
    watch: {
        job(newJob, oldJob) {
            if (!newJob || !oldJob || newJob.id !== oldJob.id) {
                this.cancelRequested = false
            }
        },
    },
    methods: {
        cancel() {
            this.cancelRequested = true
            this.$store.dispatch("jobs/cancel", this.job.id)
                .catch((error) => {
                    this.cancelRequested = false
                    this.$bvToast.toast(error, { title: "Could not cancel the job", variant: "danger" })
                })
        },
        retryFailed() {
            this.retrying = true
            this.$store.dispatch("jobs/retry", { job_id: this.job.id, only_failed: true })
                .then(job => this.$emit("retried", job))
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
.job-run {
    margin-bottom: 1rem;
}

.job-run-head {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem 1.25rem;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;
    min-height: 3.2rem;
}

.job-run-progress {
    flex: 1 1 22rem;
    min-width: 0;
}

.job-run-idle {
    flex: 1 1 22rem;
    color: var(--var-color-yankeesblue);
}

.job-run-idle-hint {
    display: block;
    color: #6c757d;
    font-size: 0.85rem;
    margin-top: 0.15rem;
}

.job-run-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.job-run-link {
    padding-left: 0.25rem;
    padding-right: 0.25rem;
}
</style>
