// Wording and icons shared by the health views

export const SEVERITY_META = {
    critical: { label: "Critical", plural: "critical", icon: "fas fa-circle-exclamation" },
    warning: { label: "Warning", plural: "warnings", icon: "fas fa-triangle-exclamation" },
    info: { label: "Info", plural: "info", icon: "fas fa-circle-info" },
}

export const CATEGORY_LABELS = {
    availability: "Availability",
    version: "Version",
    workers: "Workers",
    sync: "Sync",
    services: "Services",
    config: "Configuration",
    freshness: "Freshness",
    users: "Users",
}

// One label per rule, for grouping by issue type (finding titles vary per subject)
export const RULE_LABELS = {
    auth_failed: "Authentication failed",
    unreachable: "Server unreachable",
    slow: "Slow connection",
    stale: "Data out of date",
    fetch_error: "Data could not be fetched",
    outdated: "Outdated MISP",
    background_jobs_disabled: "Background jobs disabled",
    workers_none: "No workers",
    workers_dead: "Dead workers",
    jobs_backlog: "Job backlog",
    zmq: "ZeroMQ not working",
    proxy: "Proxy not working",
    modules: "Modules unavailable",
    sync_link: "Broken sync links",
    pending_registrations: "Pending account requests",
    baseline_drift: "Baseline drift",
    organisation_mismatch: "Organisation mismatches",
}

const TAB_ACTIONS = {
    diagnostic: { label: "Open diagnostic", icon: "fas fa-stethoscope" },
    connections: { label: "Open connections", icon: "fas fa-network-wired" },
    profile: { label: "Open user profile", icon: "fas fa-user" },
    organisations: { label: "Open organisation", icon: "fas fa-building" },
}

// What the button of an issue's suggested action says
export function actionMeta(action) {
    if (!action) {
        return null
    }
    switch (action.kind) {
        case "test_connection":
            return { label: "Test connection", icon: "fas fa-plug" }
        case "refresh":
            return { label: "Refresh now", icon: "fas fa-rotate" }
        case "edit_server":
            return { label: "Edit server", icon: "fas fa-pen" }
        case "open_tab":
            return TAB_ACTIONS[action.target] || { label: "Open server", icon: "fas fa-server" }
        case "open_misp":
            return { label: "Open in MISP", icon: "fas fa-arrow-up-right-from-square" }
        case "open_baseline":
            return { label: "Open baseline", icon: "fas fa-ruler-combined" }
        default:
            return null
    }
}

export function countsText(counts) {
    return ["critical", "warning", "info"]
        .filter(severity => counts[severity] > 0)
        .map(severity => {
            const meta = SEVERITY_META[severity]
            return `${counts[severity]} ${counts[severity] === 1 ? meta.label.toLowerCase() : meta.plural}`
        })
        .join(", ")
}
