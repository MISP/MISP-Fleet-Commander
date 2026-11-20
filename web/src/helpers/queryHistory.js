// The history of a saved query, shaped for its charts: the expectation as a line, one value axis for every server,
// what a point stands for, and each server's latest answer. Pure functions: no Vue, no store

import { formatValue } from "@/helpers/metrics"

// Where answers miss the expectation, for each comparator: above or below its line. `eq`/`ne` miss on both sides
const MISSED_SIDE = { lt: "above", lte: "above", gt: "below", gte: "below", eq: null, ne: null }

/**
 * The expectation drawn on each chart, `{ value, text, side }`, or null when it says nothing a line can show
 * (anything but 0, at least 0). Counts are never negative, so "exactly 0" and "no rows" miss above the line.
 */
export function thresholdOf(expectation, text) {
    if (!expectation || !(expectation.comparator in MISSED_SIDE)) {
        return null
    }
    const { comparator, value } = expectation
    if (typeof value !== "number" || !Number.isFinite(value)) {
        return null
    }
    let side = MISSED_SIDE[comparator]
    if (value === 0) {
        if (comparator === "eq") {
            side = "above"
        } else if (side !== "above") {
            return null
        }
    }
    return { value, text: text ? `Expected ${text}` : "", side }
}

/**
 * The value axis every chart shares, `[min, max]`: from the lowest to the highest answer of any server and the
 * expectation, with some room. It hugs the data rather than starting at 0, so that a count moving around 900 reads
 * as moving; null when there is nothing to draw
 */
export function sharedDomain(servers, threshold) {
    let lo = Infinity
    let hi = -Infinity
    const visit = (value) => {
        if (typeof value === "number" && Number.isFinite(value)) {
            lo = Math.min(lo, value)
            hi = Math.max(hi, value)
        }
    }
    ;(servers || []).forEach((entry) => {
        [entry.points, entry.lows, entry.highs].forEach((list) => (list || []).forEach(([, value]) => visit(value)))
    })
    if (lo === Infinity) {
        return null
    }
    if (threshold) {
        visit(threshold.value)
    }
    const pad = (hi - lo) * 0.15 || Math.max(1, Math.abs(hi) * 0.05)
    return [Math.max(0, lo - pad), hi + pad]
}

/** What one point of the charts stands for */
export function pointNote(history) {
    if (!history) {
        return ""
    }
    let text = {
        raw: "Each point is one answer.",
        hour: "Each point is an hour: its last answer, with a band from the lowest to the highest.",
        day: "Each point is a day: its last answer, with a band from the lowest to the highest.",
    }[history.tier] || ""
    if (history.kind === "select" && history.limit) {
        const limit = formatValue(history.limit, "count", { exact: true })
        text += ` A SELECT counts the rows it returned, at most its LIMIT: a point at ${limit} may stand for more.`
    }
    return text.trim()
}

/**
 * One chart per server, in `order` (server IDs, worst state first as in the table; the others after, as listed):
 * `{ serverId, serverName, series, latest: { ts, value, more } | null }`
 */
export function historyCharts(history, order) {
    if (!history || !Array.isArray(history.servers)) {
        return []
    }
    const byId = new Map(history.servers.map((entry) => [entry.server_id, entry]))
    const ids = (order || []).filter((id) => byId.has(id))
    history.servers.forEach((entry) => {
        if (!ids.includes(entry.server_id)) {
            ids.push(entry.server_id)
        }
    })
    const label = history.kind === "select" ? "Rows" : "Count"
    return ids.map((id) => {
        const entry = byId.get(id)
        const points = entry.points || []
        const last = points[points.length - 1]
        const capped = new Set(entry.capped || [])
        return {
            serverId: id,
            serverName: entry.server_name,
            series: [{ key: "value", label, points, peaks: entry.highs || [], lows: entry.lows || [] }],
            latest: last ? { ts: last[0], value: last[1], more: capped.has(last[0]) } : null,
        }
    })
}

/** "Latest 1,284", "Latest 100 or more", or what to say without an answer over the range */
export function latestText(latest) {
    if (!latest) {
        return "No answer over this range"
    }
    return `Latest ${formatValue(latest.value, "count", { exact: true })}${latest.more ? " or more" : ""}`
}

/** Whether any server has an answer over the range */
export function hasPoints(history) {
    return Boolean(history && (history.servers || []).some((entry) => (entry.points || []).length > 0))
}
