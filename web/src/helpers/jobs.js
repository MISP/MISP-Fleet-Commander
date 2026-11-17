// Jobs: writes sent to several servers, run by the workers. Status labels, tones and formatting shared by the
// batch modals, the job page and the notifications. Tones follow the health colours (global.css)

export const FINAL_JOB_STATUSES = ["done", "partial", "failed", "cancelled"]

export const JOB_STATUS_META = {
    queued: { label: "Queued", tone: "muted", icon: "hourglass-split", help: "Waiting for a worker" },
    running: { label: "Running", tone: "running", icon: "arrow-repeat", help: "In progress" },
    done: { label: "Done", tone: "ok", icon: "check-circle-fill", help: "Every server succeeded" },
    partial: { label: "Partly failed", tone: "warning", icon: "exclamation-triangle-fill", help: "Some servers failed" },
    failed: { label: "Failed", tone: "critical", icon: "x-circle-fill", help: "No server succeeded" },
    cancelled: { label: "Cancelled", tone: "muted", icon: "slash-circle", help: "Stopped before every server was done" },
}

export const RESULT_STATUS_META = {
    pending: { label: "Pending", tone: "muted", icon: "clock" },
    ok: { label: "OK", tone: "ok", icon: "check-circle-fill" },
    error: { label: "Error", tone: "critical", icon: "x-circle-fill" },
    skipped: { label: "Skipped", tone: "info", icon: "dash-circle-fill" },
    cancelled: { label: "Cancelled", tone: "muted", icon: "slash-circle" },
}

export const JOB_KIND_LABELS = {
    plugin_action: "Plugin action",
    plugin_quick_action: "Quick action",
    rest_query: "REST query",
    server_management: "Remote administration",
    edit_connection: "Sync connection edit",
    baseline_remediation: "Baseline remediation",
    organisation_copy: "Organisation copy",
    sharing_group_copy: "Sharing group copy",
}

// The jobs list's status filter: groups of statuses, as the API takes them (comma-separated)
export const JOB_STATUS_FILTERS = [
    { value: "", label: "All", statuses: [] },
    { value: "active", label: "In progress", statuses: ["queued", "running"] },
    { value: "failed", label: "With failures", statuses: ["failed", "partial"] },
    { value: "done", label: "Done", statuses: ["done"] },
    { value: "cancelled", label: "Cancelled", statuses: ["cancelled"] },
]

export const JOB_PERIODS = [
    { value: "", text: "Any time", seconds: null },
    { value: "24h", text: "Last 24 hours", seconds: 86400 },
    { value: "7d", text: "Last 7 days", seconds: 7 * 86400 },
    { value: "30d", text: "Last 30 days", seconds: 30 * 86400 },
]

// Results of a job as the list knows them (counters only, no per-server rows): what is neither OK nor failed but
// over was skipped or cancelled
export function jobTally(job) {
    const total = job.total || 0
    const ok = job.succeeded || 0
    const failed = job.failed || 0
    const done = Math.max(job.done || 0, ok + failed)
    return { total, ok, failed, other: Math.max(done - ok - failed, 0), pending: Math.max(total - done, 0), done }
}

export function isFinalJob(job) {
    return job !== null && job !== undefined && FINAL_JOB_STATUSES.includes(job.status)
}

export function jobStatusMeta(status) {
    return JOB_STATUS_META[status] || { label: status, tone: "muted", icon: "question-circle" }
}

export function resultStatusMeta(status) {
    return RESULT_STATUS_META[status] || { label: status, tone: "muted", icon: "question-circle" }
}

export function resultCounts(job) {
    const counts = { pending: 0, ok: 0, error: 0, skipped: 0, cancelled: 0 }
    if (job && Array.isArray(job.results)) {
        job.results.forEach((result) => {
            counts[result.status] = (counts[result.status] || 0) + 1
        })
    }
    return counts
}

// "0.3 s", "12 s", "2 min 05 s", "1 h 02 min"
export function formatDuration(seconds) {
    if (seconds === null || seconds === undefined || Number.isNaN(seconds) || seconds < 0) {
        return ""
    }
    if (seconds < 10) {
        return `${seconds.toFixed(1)} s`
    }
    if (seconds < 60) {
        return `${Math.round(seconds)} s`
    }
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) {
        return `${minutes} min ${String(Math.round(seconds % 60)).padStart(2, "0")} s`
    }
    return `${Math.floor(minutes / 60)} h ${String(minutes % 60).padStart(2, "0")} min`
}

export function resultDuration(result) {
    if (!result || !result.started || !result.finished) {
        return null
    }
    return result.finished - result.started
}

// Final state wins over a stale snapshot, and a recorded result over its pending copy: socket events and HTTP
// answers can arrive in any order
export function mergeJob(current, incoming) {
    if (!current) {
        return incoming
    }
    const merged = Object.assign({}, current, incoming)
    if (isFinalJob(current) && !isFinalJob(incoming)) {
        ["status", "finished", "succeeded", "failed"].forEach((key) => { merged[key] = current[key] })
    }
    if (Array.isArray(incoming.results)) {
        const currentById = {}
        ;(current.results || []).forEach((result) => { currentById[result.id] = result })
        merged.results = incoming.results.map((result) => {
            const known = currentById[result.id]
            return result.status === "pending" && known && known.status !== "pending" ? known : result
        })
    } else if (current.results) {
        merged.results = current.results
    }
    merged.succeeded = Math.max(current.succeeded || 0, incoming.succeeded || 0)
    merged.failed = Math.max(current.failed || 0, incoming.failed || 0)
    if (merged.results) {
        merged.done = merged.results.filter(result => result.status !== "pending").length
    }
    return merged
}
