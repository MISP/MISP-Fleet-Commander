<template>
    <div v-if="serverHasSettings">
        <div v-if="workerCount > 0 && backgroundJobEnabled">
            <div :id="`badge-workers-${server_id}`" class="badge-list d-flex flex-nowrap">
                <b-badge
                    v-for="(queue, index) in queues"
                    :key="queue.key"
                    v-b-tooltip.hover.html="{ title: queue.title }"
                    :class="[roundedClass(index), queue.badge.class]"
                    :variant="queue.badge.variant"
                >{{ queue.jobCount }}</b-badge>
            </div>
        </div>
        <b-badge
            v-else-if="backgroundJobEnabled && workerCount == 0"
            :variant="noWorkerBadge.variant"
            :class="noWorkerBadge.class"
            :title="noWorkerTitle"
            rounded
        >
            Background job enabled but no worker running
        </b-badge>
        <b-badge
            v-else
            :variant="disabledBadge.variant"
            :class="disabledBadge.class"
            :title="disabledTitle"
            rounded
        >
            Background job disabled
        </b-badge>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import { healthCellMixin, toneBadge, toneTitle } from "@/helpers/healthCells"

// In the order of the cell. `key` is the queue name in MISP's diagnostics (and the issue's subject)
const QUEUES = [
    { key: "cache", label: "cache" },
    { key: "default", label: "default" },
    { key: "prio", label: "prio" },
    { key: "update", label: "update", noBacklog: true },
    { key: "email", label: "mail" },
]
const QUEUE_RULES = ["workers_none", "workers_dead", "jobs_backlog"]

function escapeHtml(text) {
    return String(text).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]))
}

function aliveNumbers(queue) {
    const workers = Object.values((queue && queue.workers) || {})
    const dead = workers.filter(worker => !worker.ok).length
    return { dead, alive: workers.length - dead, total: workers.length }
}

export default {
    name: "workersStatus",
    mixins: [healthCellMixin],
    props: {
        workers: {
        },
        server_id: {
            type: Number,
            required: true
        }
    },
    computed: {
        ...mapState({
            final_settings: state => state.servers.final_settings,
        }),
        ...mapGetters({
            getLoggedUserSettingByName: "userSettings/getLoggedUserSettingsByName",
        }),
        // Only used until health is loaded: the engine applies the same user settings
        workerWarningThreshold() {
            if (this.getLoggedUserSettingByName && this.getLoggedUserSettingByName['UI.server_index.worker_warning_threshold']) {
                return parseInt(this.getLoggedUserSettingByName['UI.server_index.worker_warning_threshold'])
            }
            return 10
        },
        workerDangerThreshold() {
            if (this.getLoggedUserSettingByName && this.getLoggedUserSettingByName['UI.server_index.worker_danger_threshold']) {
                return parseInt(this.getLoggedUserSettingByName['UI.server_index.worker_danger_threshold'])
            }
            return 100
        },
        backgroundJobEnabled() {
            return this.final_settings[this.server_id]['MISP.background_jobs']
        },
        serverHasSettings() {
            return this.final_settings[this.server_id] !== undefined && Object.keys(this.final_settings[this.server_id]).length > 0
        },
        workerCount() {
            return Object.keys(this.workers || {}).length
        },
        queues() {
            return QUEUES.map((meta) => {
                const queue = (this.workers && this.workers[meta.key]) || {}
                const numbers = aliveNumbers(queue)
                const tone = this.healthTone(this.server_id, QUEUE_RULES, { subject: meta.key })
                return {
                    ...meta,
                    jobCount: queue.jobCount,
                    badge: tone === null ? { variant: this.fallbackVariant(meta, queue, numbers), class: "" } : toneBadge(tone),
                    title: this.queueTitle(meta.label, queue.jobCount, numbers, tone),
                }
            })
        },
        noWorkerTone() {
            return this.healthTone(this.server_id, "workers_none")
        },
        noWorkerBadge() {
            return this.noWorkerTone === null ? { variant: "danger", class: "" } : toneBadge(this.noWorkerTone, "secondary")
        },
        noWorkerTitle() {
            return toneTitle(this.noWorkerTone)
        },
        disabledTone() {
            return this.healthTone(this.server_id, "background_jobs_disabled")
        },
        disabledBadge() {
            return this.disabledTone === null ? { variant: "danger", class: "" } : toneBadge(this.disabledTone, "secondary")
        },
        disabledTitle() {
            return toneTitle(this.disabledTone)
        },
    },
    methods: {
        fallbackVariant(meta, queue, numbers) {
            if (numbers.total == 0) {
                return "danger"
            }
            if (numbers.dead > 0) {
                return numbers.dead == numbers.total ? "danger" : "warning"
            }
            if (meta.noBacklog || queue.jobCount <= this.workerWarningThreshold) {
                return ""
            }
            return queue.jobCount <= this.workerDangerThreshold ? "warning" : "danger"
        },
        queueTitle(label, jobCount, numbers, tone) {
            const workers = numbers.total == 0 ? "No worker running" : `${numbers.alive}/${numbers.total} alive`
            const why = toneTitle(tone)
            return `Worker <strong>${escapeHtml(label)}</strong><div class="text-left">${escapeHtml(jobCount ?? "?")} in queue<br>${workers}`
                + (why ? `<br><em>${escapeHtml(why).replace(/\n/g, "<br>")}</em>` : "")
                + "</div>"
        },
        roundedClass(index) {
            if (index === 0) {
                return "rounded-left flat-right"
            }
            return index === QUEUES.length - 1 ? "rounded-right flat-left" : "rounded-0"
        },
    }
}
</script>

<style scoped>
    .badge-list {
        width: fit-content;
    }

    .badge-list > .badge {
        cursor: default;
    }

    .badge-list > .badge:not(:last-child) {
        border-right: 1px solid #dee2e6
    }

    .flat-right {
        border-top-right-radius: 0;
        border-bottom-right-radius: 0;
    }

    .flat-left {
        border-top-left-radius: 0;
        border-bottom-left-radius: 0
    }
</style>
