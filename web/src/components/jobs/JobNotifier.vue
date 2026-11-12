<template>
    <span class="d-none" aria-hidden="true"></span>
</template>

<script>
import { mapState } from "vuex"

const VARIANTS = {
    done: "success",
    partial: "warning",
    failed: "danger",
    cancelled: "secondary",
}

export function jobOutcomeMessage(job) {
    const servers = (count) => `${count} server${count === 1 ? "" : "s"}`
    if (job.status === "done") {
        return job.total === 1 ? "Succeeded." : `Succeeded on all ${servers(job.total)}.`
    }
    if (job.status === "partial") {
        return `${job.succeeded} succeeded, ${job.failed} failed.`
    }
    if (job.status === "failed") {
        return job.total === 1 ? "Failed." : `Failed on ${servers(job.failed)}: no server succeeded.`
    }
    return `Cancelled after ${servers(job.succeeded + job.failed)}.`
}

export function startedToastId(job_id) {
    return `job-toast-${job_id}`
}

// Announces the end of the jobs started from this tab, wherever the user is by then. The toast opens the job
export default {
    name: "JobNotifier",
    computed: {
        ...mapState({
            finished: state => state.jobs.finished,
        }),
    },
    watch: {
        finished(entries) {
            if (entries.length === 0) {
                return
            }
            const jobs = entries.slice()
            this.$store.commit("jobs/takeFinished")
            jobs.forEach(job => this.announce(job))
        },
    },
    methods: {
        announce(job) {
            this.$bvToast.hide(startedToastId(job.id))
            const h = this.$createElement
            const body = h("div", [
                h("div", jobOutcomeMessage(job)),
                h("div", { class: "small mt-1" }, [
                    "See each server's result ",
                    h("i", { class: "fas fa-arrow-right", attrs: { "aria-hidden": "true" } }),
                ]),
            ])
            this.$bvToast.toast(body, {
                title: job.title,
                variant: VARIANTS[job.status] || "info",
                to: { name: "jobs.view", params: { job_id: job.id } },
                autoHideDelay: job.status === "done" ? 6000 : 12000,
                solid: true,
            })
        },
    },
}
</script>
