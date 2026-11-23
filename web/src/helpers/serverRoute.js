// The server page reads its server from the selected fleet's servers. Opening a server of another fleet (Attention,
// job results, a saved query, the navbar search all link across fleets), or before the fleet's servers are loaded,
// first selects the server's fleet.

/** Whether two server page routes show the same server: a link may give its ID as a number, the URL as text */
export function sameServer(to, from) {
    return String(to.params.server_id) === String(from.params.server_id)
}

/** Whether the store already holds `serverId` among the selected fleet's servers */
export function serverInSelectedFleet(store, serverId) {
    const servers = (store.state.servers && store.state.servers.servers) || {}
    return store.getters["fleets/selectedFleet"] !== null && Boolean(servers[serverId])
}

/**
 * Select `serverId`'s fleet and load its servers, unless the store already holds it. Resolves with whether the fleet
 * was selected again (its servers then still loading); rejects when the server is unknown
 */
export function selectServerFleet(store, serverId) {
    if (serverInSelectedFleet(store, serverId)) {
        return Promise.resolve(false)
    }
    return store.dispatch("fleets/selectFleetFromServerId", serverId).then(() => {
        store.dispatch("servers/fetchServers", { force: true })
        return true
    })
}
