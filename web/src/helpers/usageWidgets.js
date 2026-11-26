// Widgets of a fleet's Usage tab: saved queries followed there, drawn as the fleet total or server by server. Pure
// functions: no Vue, no store

import { agoText, changeOver, formatChangePct, formatDelta, formatValue } from "@/helpers/metrics"
import { overviewParts } from "@/helpers/savedQueries"

// Charts shown at once in an "Each server" widget, before "Show all"
export const SHOWN_SERVERS = 6

export const DISPLAYS = [
    { key: "total", label: "Fleet total", icon: "fa-chart-line", text: "One line: the fleet's servers' answers summed" },
    { key: "servers", label: "Each server", icon: "fa-th-large", text: "One small chart per server, with the expectation" },
]

const SCHEDULE_WORDS = { 15: "every 15 min", 60: "hourly", 360: "every 6 h", 720: "every 12 h", 1440: "daily" }

/** "every 15 min", "hourly"… or "run by hand" */
export function scheduleWords(minutes) {
    if (minutes === null || minutes === undefined) {
        return "run by hand"
    }
    return SCHEDULE_WORDS[minutes] || `every ${minutes} min`
}

/** One line under a widget's name: "COUNT · hourly · expects at most 900" */
export function widgetFacts(saved) {
    if (!saved) {
        return ""
    }
    const parts = [saved.kind ? saved.kind.toUpperCase() : "", scheduleWords(saved.schedule_minutes)]
    if (saved.expectation_text) {
        parts.push(`expects ${saved.expectation_text}`)
    }
    return parts.filter(Boolean).join(" · ")
}

/** How the fleet's servers last answered, worst first: `[{ state, count, text, tone, icon }]` */
export function standingParts(servers, severity) {
    const overview = {}
    ;(servers || []).forEach((entry) => {
        overview[entry.state] = (overview[entry.state] || 0) + 1
    })
    return overviewParts(overview, severity)
}

/** Where a candidate runs, from the fleet's point of view */
export function candidateWhere(candidate, fleetServers) {
    if (candidate.aims_at_fleet) {
        return "On this fleet"
    }
    if (candidate.fleet_servers === fleetServers) {
        return { 1: "On this fleet's server", 2: "On both of this fleet's servers" }[fleetServers]
            || `On all ${fleetServers} of this fleet's servers`
    }
    const of = `${candidate.fleet_servers} of this fleet's ${fleetServers} server${fleetServers === 1 ? "" : "s"}`
    return `On ${of}`
}

/**
 * The fleet total of a widget's history, for its chart and its figure: `{ series, latest, change, servers }`, or
 * null without a total. `latest` = `{ ts, value, more, reporting }`: the last point, whether a SELECT's answer in it
 * stood at its LIMIT, and how many servers it sums
 */
export function totalView(history) {
    const total = history && history.total
    if (!total) {
        return null
    }
    const points = total.points || []
    const capped = new Set(total.capped || [])
    const reporting = new Map((total.reporting || []).map(([ts, count]) => [ts, count]))
    const last = points[points.length - 1]
    return {
        series: [{ key: "total", label: history.kind === "select" ? "Rows" : "Count", points, band: false }],
        latest: last ? { ts: last[0], value: last[1], more: capped.has(last[0]), reporting: reporting.get(last[0]) || 0 } : null,
        change: changeOver(points),
        servers: total.servers || 0,
    }
}

/** "1,284", "100 or more" */
export function totalValueText(latest) {
    if (!latest) {
        return "—"
    }
    return `${formatValue(latest.value, "count", { exact: true })}${latest.more ? " or more" : ""}`
}

/** "+12 (+0.5%)", "No change", or "" with fewer than two points */
export function changeText(change) {
    if (!change) {
        return ""
    }
    if (change.abs === 0) {
        return "No change"
    }
    const pct = formatChangePct(change.pct)
    return `${formatDelta(change.abs, "count")}${pct ? ` (${pct})` : ""}`
}

/** What one point of a fleet total stands for; `single`: the total of the one server the tab is limited to */
export function totalNote(history, { single = false } = {}) {
    const total = history && history.total
    if (!total) {
        return ""
    }
    const bucket = total.tier === "day" ? "a day" : "an hour"
    const unit = total.tier === "day" ? "day" : "hour"
    const limit = history.kind === "select" && history.limit ? formatValue(history.limit, "count", { exact: true }) : null
    if (single) {
        let text = `Each point is ${bucket}: the server's last answer that ${unit}, or its previous one when it gave none.`
        if (limit) {
            text += ` A SELECT counts the rows it returned, at most ${limit}: a point at its LIMIT may stand for more.`
        }
        return text
    }
    let text = `Each point is ${bucket}: each server's last answer, summed. A server without an answer that ${unit} `
        + "counts with its previous one."
    if (limit) {
        text += ` A SELECT counts the rows it returned, at most ${limit} each: a total holding one at its LIMIT may stand for more.`
    }
    return text
}

/**
 * The old answers the latest total still holds: servers whose last run gave no number, their last answer carried
 * forward (`history.total.carried`, ages from the answer's time). `{ text, title }`, or null when every number in it
 * is current: "Includes Refused org test's last answer (471), 12 days old"
 */
export function carriedText(history) {
    const total = history && history.total
    const carried = (total && total.carried) || []
    if (carried.length === 0) {
        return null
    }
    const number = (value, more) => `${formatValue(value, "count", { exact: true })}${more ? " or more" : ""}`
    const age = (ts) => `${agoText(Math.max(0, total.to - ts))} old`
    if (carried.length === 1) {
        const [entry] = carried
        return {
            text: `Includes ${entry.server_name}'s last answer (${number(entry.value, entry.more)}), ${age(entry.ts)}`,
            title: "Its last run gave no number: the total keeps its last answer until it answers again.",
        }
    }
    const sum = carried.reduce((acc, entry) => acc + entry.value, 0)
    const oldest = Math.min(...carried.map((entry) => entry.ts))
    const lines = carried.map((entry) => `${entry.server_name}: ${number(entry.value, entry.more)}, ${age(entry.ts)}`)
    return {
        text: `Includes ${carried.length} servers' last answers (${number(sum, carried.some((entry) => entry.more))}), `
            + `the oldest ${age(oldest)}`,
        title: ["Their last run gave no number: the total keeps each one's last answer until it answers again.", ...lines]
            .join("\n"),
    }
}

/** Servers the latest total leaves out because they never answered: "2 of 3 servers answered so far", or "" */
export function reportingText(view) {
    if (!view || !view.latest || view.latest.reporting >= view.servers) {
        return ""
    }
    return `${view.latest.reporting} of ${view.servers} servers answered so far`
}

/**
 * How wide each widget is on a wide screen, in their order: two Fleet totals in a row share it; a widget alone in
 * its row (Each server, or a Fleet total without another one next to it) takes it whole. `{ [id]: "half" | "full" }`
 */
export function widgetSpans(widgets) {
    const spans = {}
    let index = 0
    while (index < widgets.length) {
        const current = widgets[index]
        const next = widgets[index + 1]
        if (current.display === "total" && next && next.display === "total") {
            spans[current.id] = "half"
            spans[next.id] = "half"
            index += 2
        } else {
            spans[current.id] = "full"
            index += 1
        }
    }
    return spans
}

/** The widget IDs with `id` moved `delta` places (−1 up, +1 down); the same order when it cannot move */
export function movedIds(ids, id, delta) {
    const from = ids.indexOf(id)
    const to = from + delta
    if (from < 0 || to < 0 || to >= ids.length) {
        return ids.slice()
    }
    const moved = ids.slice()
    moved.splice(from, 1)
    moved.splice(to, 0, id)
    return moved
}

/** Why a widget has nothing to draw, in words; `serverName`: the one server the tab is limited to */
export function problemText(problem, serverName = "") {
    return {
        no_number: "Its statement no longer answers a number (only a SELECT or a COUNT does).",
        no_server: serverName ? `It does not run on ${serverName} now.` : "It runs on none of this fleet's servers now.",
    }[problem] || ""
}
