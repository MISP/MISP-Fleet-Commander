import common from "./common"

// The stored usage metrics of a server or a fleet, and a server's live endpoint benchmarks. Kept by the Usage tabs
// themselves: nothing else shares this data, so it has no store module
function query({ range, tier, metrics, serverId } = {}) {
    const params = new URLSearchParams()
    if (range) params.set("range", range)
    if (tier) params.set("tier", tier)
    if (metrics && metrics.length > 0) params.set("metrics", metrics.join(","))
    if (serverId !== null && serverId !== undefined) params.set("server_id", String(serverId))
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

    /** The fleet's servers summed per hour or day, and each server's figures: `{totals, reporting, servers,
     * fleet_servers, server_id, state, metrics, tier, interval_s, partial_since, latest_ts, from, to}`; `options` takes
     * `range`, `metrics` and `serverId` (only that server of the fleet) */
    fleetSeries(fleetId, { range, metrics, serverId } = {}) {
        // A refusal rejects with an Error holding the server's message and the `status` (400: a server not in the
        // fleet), which the client's own handling would reduce to the message
        return common.getClient().get(`/fleets/metrics/${fleetId}${query({ range, metrics, serverId })}`, {
            validateStatus: (status) => (status >= 200 && status < 300) || status === 400,
        }).then((response) => {
            if (response.status === 400) {
                const error = new Error((response.data && response.data.message) || "The request was refused")
                error.status = 400
                throw error
            }
            return response.data
        })
    },

    /** Today's most expensive endpoints: `{date, timestamp, cached, fields: {time|sql_time|memory: {unit, top}}}` */
    benchmarks(serverId, refresh = false) {
        return common.getClient().get(`/servers/benchmarks/${serverId}${refresh ? "?refresh=1" : ""}`)
            .then((response) => response.data)
    },
}
