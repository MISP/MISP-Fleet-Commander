import common from "./common"

// The stored usage metrics of a server and its live endpoint benchmarks. Kept by the Usage tab itself: nothing else
// shares this data, so it has no store module
export default {
    /** `{series, peaks, latest, state, metrics, tier, interval_s, partial_since, from, to}`; `options` takes `range`,
     * `tier` and `metrics` (a list of keys) */
    series(serverId, { range, tier, metrics } = {}) {
        const params = new URLSearchParams()
        if (range) params.set("range", range)
        if (tier) params.set("tier", tier)
        if (metrics && metrics.length > 0) params.set("metrics", metrics.join(","))
        const query = params.toString()
        return common.getClient().get(`/servers/metrics/${serverId}${query ? `?${query}` : ""}`)
            .then((response) => response.data)
    },

    /** Today's most expensive endpoints: `{date, timestamp, cached, fields: {time|sql_time|memory: {unit, top}}}` */
    benchmarks(serverId, refresh = false) {
        return common.getClient().get(`/servers/benchmarks/${serverId}${refresh ? "?refresh=1" : ""}`)
            .then((response) => response.data)
    },
}
