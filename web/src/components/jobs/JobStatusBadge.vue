<template>
    <span
        :class="['job-status', `job-tone-${meta.tone}`, { 'job-status-small': small }]"
        :title="meta.help || meta.label"
    >
        <b-icon
            :icon="meta.icon"
            :animation="spinning ? 'spin' : ''"
            class="job-status-icon"
            aria-hidden="true"
        ></b-icon>
        <span>{{ meta.label }}</span>
    </span>
</template>

<script>
import { jobStatusMeta, resultStatusMeta } from "@/helpers/jobs"

export default {
    name: "JobStatusBadge",
    props: {
        status: {
            type: String,
            required: true,
        },
        // `job` or `result`: the two have their own statuses
        of: {
            type: String,
            default: "job",
        },
        small: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        meta() {
            return this.of === "result" ? resultStatusMeta(this.status) : jobStatusMeta(this.status)
        },
        spinning() {
            return this.of === "job" && this.status === "running"
        },
    },
}
</script>

<style scoped>
.job-status {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.15rem 0.55rem 0.15rem 0.45rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    line-height: 1.3;
    white-space: nowrap;
    color: var(--job-ink);
    background: var(--job-tint);
}

.job-status-small {
    font-size: 0.75rem;
    padding: 0.05rem 0.45rem 0.05rem 0.35rem;
}

.job-status-icon {
    flex: none;
    font-size: 0.9em;
}
</style>
