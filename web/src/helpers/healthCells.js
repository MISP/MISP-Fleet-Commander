import { mapState } from "vuex"
import { severityRank, worstSeverity } from "@/store/modules/health"

// Status cells (fleet table, server page, Strategic View, Connections page) take their colour from the health
// issues of the server instead of thresholds of their own. A cell asks for the issues of one or more rules,
// optionally of one subject (a worker queue, a module, a sync link), and gets a tone:
//   - level: "critical" | "warning" | "info" (worst issue), "ok" (no issue), or "unchecked";
//   - acked: true when every matching issue is acknowledged: the problem is still there, drawn muted;
//   - issues: the matching issues, most severe first.
// `null` means health is not loaded yet: the cell falls back to its own logic.

export const SEVERITY_VARIANT = { critical: "danger", warning: "warning", info: "info" }

// While one of these is reported, rules reading the snapshot's content are skipped (the engine's root cause rule):
// what the snapshot still shows was not checked
function serverUnchecked(issues) {
    return issues.some(issue => issue.category === "availability" && issue.severity === "critical")
}

export function healthTone(issues, { rules, subject = null, content = true }) {
    const ruleList = Array.isArray(rules) ? rules : [rules]
    const matching = issues
        .filter(issue => ruleList.includes(issue.rule) && (subject === null || issue.subject === String(subject)))
        .sort((a, b) => severityRank(a.severity) - severityRank(b.severity))
    const active = matching.filter(issue => issue.ack === null)
    if (active.length > 0) {
        return { level: worstSeverity(active), acked: false, issues: matching }
    }
    if (matching.length > 0) {
        return { level: worstSeverity(matching), acked: true, issues: matching }
    }
    if (content && serverUnchecked(issues)) {
        return { level: "unchecked", acked: false, issues: [] }
    }
    return { level: "ok", acked: false, issues: [] }
}

export function isProblem(tone) {
    return tone !== null && SEVERITY_VARIANT[tone.level] !== undefined
}

// Text colour: `okClass` is what the cell shows when all is well (green for a status, muted for a date)
export function toneTextClass(tone, okClass = "text-success") {
    if (tone === null) {
        return ""
    }
    if (tone.acked) {
        return `health-acked health-acked-${tone.level}`
    }
    switch (tone.level) {
        case "critical": return "text-danger"
        case "warning": return "health-ink-warning"
        case "info": return "text-info"
        case "unchecked": return "text-muted"
        default: return okClass
    }
}

// Badge look: a bootstrap variant, plus a class for acknowledged issues (light badge, muted ink, dashed outline)
export function toneBadge(tone, okVariant = "") {
    if (tone === null) {
        return { variant: okVariant, class: "" }
    }
    if (tone.acked) {
        return { variant: "light", class: `health-acked-badge health-acked-${tone.level}` }
    }
    if (tone.level === "unchecked") {
        return { variant: "light", class: "" }
    }
    return { variant: SEVERITY_VARIANT[tone.level] || okVariant, class: "" }
}

// Tooltip line saying why the cell has its colour
export function toneTitle(tone) {
    if (tone === null) {
        return ""
    }
    if (tone.level === "unchecked") {
        return "Not checked: the server cannot be queried"
    }
    return tone.issues
        .map(issue => (issue.ack !== null ? `${issue.title} (acknowledged)` : issue.title))
        .join("\n")
}

// Connection test colours used until health is loaded
export function fallbackStatusClass(status) {
    return status && status.error ? "text-danger" : "text-success"
}

export function fallbackLatencyClass(latency) {
    if (latency < 0.3) {
        return "text-success"
    }
    return latency < 2 ? "text-warning" : "text-danger"
}

export const healthCellMixin = {
    computed: {
        ...mapState({
            healthLoaded: state => state.health.loaded,
            healthIssuesByServer: state => state.health.issuesByServer,
        }),
    },
    methods: {
        // `content: false` for rules the engine runs even when the server cannot be queried (availability, freshness)
        healthTone(server_id, rules, options = {}) {
            if (!this.healthLoaded || server_id === undefined || server_id === null) {
                return null
            }
            return healthTone(this.healthIssuesByServer[server_id] || [], { rules, ...options })
        },
        // The connection test result: reachable/authenticated, and how long it took
        connectionStatusTone(server_id) {
            return this.healthTone(server_id, ["unreachable", "auth_failed"], { content: false })
        },
        connectionStatusClass(server_id, status) {
            const tone = this.connectionStatusTone(server_id)
            return tone === null ? fallbackStatusClass(status) : toneTextClass(tone)
        },
        // Same colours as a badge, for the Strategic View nodes
        connectionStatusBadgeClass(server_id, status) {
            const tone = this.connectionStatusTone(server_id)
            if (tone === null) {
                return status && status.error ? "badge-danger" : "badge-success"
            }
            const badge = toneBadge(tone, "success")
            return [`badge-${badge.variant}`, badge.class]
        },
        latencyTone(server_id) {
            return this.healthTone(server_id, "slow", { content: false })
        },
        latencyClass(server_id, latency) {
            const tone = this.latencyTone(server_id)
            return tone === null ? fallbackLatencyClass(latency) : toneTextClass(tone)
        },
    },
}
