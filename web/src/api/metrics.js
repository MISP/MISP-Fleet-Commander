import common from "./common"

// The stored usage metrics of a server or a fleet, and a server's live endpoint benchmarks. Kept by the Usage tabs
// themselves: nothing else shares this data, so it has no store module
function query({ range, tier, metrics } = {}) {
    const params = new URLSearchParams()
    if (range) params.set("range", range)
    if (tier) params.set("tier", tier)
    if (metrics && metrics.length > 0) params.set("metrics", metrics.join(","))
    const text = params.toString()
    return text ? `?${text}` : ""
}

export default {
    /** `{series, peaks, latest, state, metrics, tier, interval_s, partial_since, from, to}`; `options` takes `range`,
     * `tier` and `metrics` (a list of keys) */
    series(serverId, options = {}) {
        return common.getClient().get(`/servers/metrics/${serverId}${query(options)}`)
            .then((response) => response.data)
    },

    /** The fleet's servers summed per hour or day, and each server's figures: `{totals, reporting, servers, state,
     * metrics, tier, interval_s, partial_since, latest_ts, from, to}`; `options` takes `range` and `metrics` */
    fleetSeries(fleetId, { range, metrics } = {}) {
        return common.getClient().get(`/fleets/metrics/${fleetId}${query({ range, metrics })}`)
            .then((response) => response.data)
    },

    /** Today's most expensive endpoints: `{date, timestamp, cached, fields: {time|sql_time|memory: {unit, top}}}` */
    benchmarks(serverId, refresh = false) {
        return common.getClient().get(`/servers/benchmarks/${serverId}${refresh ? "?refresh=1" : ""}`)
            .then((response) => response.data)
    },
}
