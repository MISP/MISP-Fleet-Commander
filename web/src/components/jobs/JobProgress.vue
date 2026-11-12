<template>
    <div class="job-progress">
        <div class="job-progress-head">
            <JobStatusBadge :status="job.status"></JobStatusBadge>
            <span class="job-progress-count" aria-live="polite">
                <strong>{{ done }}</strong> / {{ total }} server{{ total === 1 ? '' : 's' }} done
            </span>
            <span class="job-progress-tally">
                <span v-if="counts.ok" class="tally job-tone-ok">{{ counts.ok }} OK</span>
                <span v-if="counts.error" class="tally job-tone-critical">{{ counts.error }} failed</span>
                <span v-if="counts.skipped" class="tally job-tone-info">{{ counts.skipped }} skipped</span>
                <span v-if="counts.cancelled" class="tally job-tone-muted">{{ counts.cancelled }} cancelled</span>
            </span>
            <span v-if="elapsedLabel" class="job-progress-time" :title="timeTitle">
                <i class="far fa-clock mr-1" aria-hidden="true"></i>{{ elapsedLabel }}
            </span>
        </div>
        <div
            class="job-progress-bar"
            role="progressbar"
            :aria-valuenow="done"
            aria-valuemin="0"
            :aria-valuemax="total"
            :aria-label="`${done} of ${total} servers done`"
        >
            <span
                v-for="segment in segments"
                :key="segment.status"
                :class="['job-progress-segment', `job-tone-${segment.tone}`]"
                :style="{ width: `${segment.percent}%` }"
            ></span>
            <span
                v-if="!final && total > done"
                class="job-progress-pending"
                :style="{ width: `${100 * (total - done) / total}%` }"
            ></span>
        </div>
    </div>
</template>

<script>
import JobStatusBadge from "@/components/jobs/JobStatusBadge.vue"
import { formatDuration, isFinalJob, resultCounts } from "@/helpers/jobs"

const SEGMENTS = [
    { status: "ok", tone: "ok" },
    { status: "error", tone: "critical" },
    { status: "skipped", tone: "info" },
    { status: "cancelled", tone: "muted" },
]

export default {
    name: "JobProgress",
    components: {
        JobStatusBadge,
    },
    props: {
        job: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            now: Date.now() / 1000,
            ticker: null,
        }
    },
    computed: {
        final() {
            return isFinalJob(this.job)
        },
        counts() {
            return resultCounts(this.job)
        },
        total() {
            return this.job.total || 0
        },
        done() {
            if (!Array.isArray(this.job.results)) {
                return this.job.done || 0
            }
            return this.total - this.counts.pending
        },
        segments() {
            if (this.total === 0) {
                return []
            }
            return SEGMENTS
                .map(segment => Object.assign({ percent: 100 * this.counts[segment.status] / this.total }, segment))
                .filter(segment => segment.percent > 0)
        },
        elapsedLabel() {
            if (!this.job.started) {
                return this.job.status === "queued" ? "Waiting for a worker" : ""
            }
            const end = this.job.finished || this.now
            return formatDuration(end - this.job.started)
        },
        timeTitle() {
            if (!this.job.started) {
                return ""
            }
            const started = new Date(this.job.started * 1000).toLocaleString()
            return this.job.finished
                ? `Started ${started}, ended ${new Date(this.job.finished * 1000).toLocaleString()}`
                : `Started ${started}`
        },
    },
    watch: {
        final: {
            immediate: true,
            handler(final) {
                // A running clock while the job runs, nothing to tick for once it is over
                clearInterval(this.ticker)
                this.ticker = null
                if (!final) {
                    this.ticker = setInterval(() => { this.now = Date.now() / 1000 }, 1000)
                }
            },
        },
    },
    beforeDestroy() {
        clearInterval(this.ticker)
    },
}
</script>

<style scoped>
.job-progress-head {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem 0.9rem;
    margin-bottom: 0.45rem;
}

.job-progress-count {
    color: var(--var-color-yankeesblue);
    font-variant-numeric: tabular-nums;
}

.job-progress-tally {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    font-size: 0.85rem;
    font-variant-numeric: tabular-nums;
}

.tally {
    color: var(--job-ink);
    font-weight: 600;
}

.job-progress-time {
    margin-left: auto;
    color: #5a6270;
    font-size: 0.85rem;
    font-variant-numeric: tabular-nums;
}

.job-progress-bar {
    display: flex;
    height: 8px;
    border-radius: 4px;
    overflow: hidden;
    background: #eceff3;
}

.job-progress-segment {
    background: var(--job-fill);
    transition: width 0.3s ease;
}

.job-progress-pending {
    background-image: linear-gradient(90deg, #eceff3 0%, #dfe5ec 50%, #eceff3 100%);
    background-size: 200% 100%;
    animation: job-progress-wait 1.6s linear infinite;
}

@keyframes job-progress-wait {
    from { background-position: 100% 0; }
    to { background-position: -100% 0; }
}

@media (prefers-reduced-motion: reduce) {
    .job-progress-segment { transition: none; }
    .job-progress-pending { animation: none; }
}
</style>
