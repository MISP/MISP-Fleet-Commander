import api from "@/api/servers"
import Vue from "vue"

// initial state
const init_state = () => {
    return {
        fetching_servers_in_progress: false,
        servers: {},
        server_status: {},
        server_query_in_progress: {},
        server_refresh_enqueued: {},
        server_status_refresh_enqueued: {},
        // server_id -> {testing, error, updated}: link tests in progress, why the last one could not be done
        server_link_test: {},
        server_query_error: {},
        server_user: {},
        remote_connections: {},
        submodules: {},
        proxy: {},
        zeromq: {},
        workers: {},
        server_users: {},
        server_usage: {},
        last_refresh: {},
        final_settings: {},
        raw_final_settings: {},
        diagnostic_full: {},
        // server_id -> timestamp of the full snapshot loaded (lists only carry a light one, see `fetchFullInfo`)
        full_info: {},
    }
}

// Full snapshot requests in flight, by server
const fullInfoRequests = {}
// The server list request on its way, `{ fleetId, promise }`, or null (see `fetchServers`)
let indexRequest = null

const state = init_state()

// getters
const getters = {
    serverCount: state => {
        return Object.keys(state.servers).length
    },
    getServerList: state => {
        return Object.values(state.servers)
    },
    serversByURL: state => {
        let serversByURL = {}
        Object.values(state.servers).forEach(server => {
            const server_url = server.url.endsWith('/') ? server.url.substr(0, server.url.length - 1) : server.url
            serversByURL[server_url] = server
        })
        return serversByURL
    },
    serversByUUID: state => {
        let serversByUUID = {}
        Object.values(state.servers).forEach(server => {
            if (state.final_settings[server.id] !== undefined) {
                const server_uuid = state.final_settings[server.id]['MISP.uuid']
                serversByUUID[server_uuid] = server
            }
        })
        return serversByUUID
    },
    getServerRefreshEnqueued: state => {
        return Object.entries(state.server_refresh_enqueued)
    }
}

// actions
// API Usage: api.[action]({parameters}, callback, errorCallback)
const actions = {

    resetState({ commit }, payload) {
        return new Promise((resolve, reject) => {
            commit("resetState")
            resolve()
        })
    },
    /**
     * The selected fleet's servers. `force`: fetched again even when loaded. A request already on its way for the same
     * fleet is shared (opening a fleet's page, the router and the page both ask for the list), except with `fresh`:
     * after a change, a request sent before it may not hold it. Only the latest request's answer is kept
     */
    fetchServers({ commit, getters, rootState }, payload = {}) {
        const selectedFleetId = () => (rootState.fleets.selected ? rootState.fleets.selected.id : null)
        const fleetId = selectedFleetId()
        if (indexRequest !== null && indexRequest.fleetId === fleetId && !payload.fresh) {
            return indexRequest.promise
        }
        if (!payload.force && !payload.fresh && getters.serverCount > 0) {
            return Promise.resolve("Server already loaded")
        }
        commit("setFetchingServersInProgress", true)
        const request = { fleetId }
        request.promise = new Promise((resolve, reject) => {
            api.index(
                (servers) => {
                    // Another fleet chosen since, or a later request on its way: theirs is the list to show
                    if (indexRequest === request && selectedFleetId() === fleetId) {
                        commit("setServers", servers)
                    }
                    resolve()
                },
                (error) => { reject(error) }
            )
        }).finally(() => {
            if (indexRequest === request) {
                indexRequest = null
                commit("setFetchingServersInProgress", false)
            }
        })
        indexRequest = request
        return request.promise
    },
    getUsers({ commit }, server_id) {
        return new Promise((resolve, reject) => {
            api.queryGetUsers(
                server_id,
                (users) => {
                    commit("updateUsers", { server_id: server_id, users: users})
                    resolve()
                },
                (error) => { 
                    reject(error)
                }
            )
        })
    },
    // The server page needs what lists leave out (MISP's settings, diagnostics): asked for once per snapshot
    fetchFullInfo({ commit, dispatch, state }, { server_id, retried = false }) {
        const loaded = state.full_info[server_id]
        if (loaded !== undefined && loaded === (state.last_refresh[server_id] || null)) {
            return Promise.resolve()
        }
        if (fullInfoRequests[server_id] === undefined) {
            fullInfoRequests[server_id] = new Promise((resolve, reject) => {
                api.queryInfo(
                    { server_id },
                    (info) => {
                        const hasSnapshot = info !== null && typeof info === "object" && info.query_result !== undefined
                        const known = state.last_refresh[server_id] || null
                        if (hasSnapshot && known !== null && info.timestamp < known) {
                            // A refresh landed while this was asked for: ask again rather than show older data
                            resolve(false)
                            return
                        }
                        if (hasSnapshot) {
                            commitAllQueryInfo(commit, server_id, info)
                        }
                        commit("setFullInfo", { server_id, timestamp: hasSnapshot && info.timestamp ? info.timestamp : null })
                        resolve(true)
                    },
                    reject,
                )
            })
                .finally(() => {
                    delete fullInfoRequests[server_id]
                })
                .then((applied) => {
                    if (applied === false && !retried) {
                        return dispatch("fetchFullInfo", { server_id, retried: true })
                    }
                })
        }
        return fullInfoRequests[server_id]
    },
    commitAllQueryInfo({ commit, dispatch }, payload) {
        return new Promise((resolve, reject) => {
            const serverID = payload.server.id
            commit("setServerRefreshEnqueued", {server_id: serverID, is_enqueued: false})
            commitAllQueryInfo(commit, serverID, payload);
            resolve()
        })
    },
    commitConnectionTestInfo({ commit }, payload) {
        return new Promise((resolve, reject) => {
            const serverID = payload.server.id
            commit("setServerStatusRefreshEnqueued", {server_id: serverID, is_enqueued: false})
            commit("setConnectionState", {server_id: serverID, connectionState: payload})
            resolve()
        })
    },
    commitPartialServerData({ commit }, payload) {
        return new Promise((resolve, reject) => {
            const server_id = payload.server_id
            const partial_data_key = payload.partial_data_key
            const partial_data = payload.data
            if (partial_data_key == 'connectedServers') {
                commit("setRemoteConnections", { server_id: server_id, connections: partial_data })
            }
            if (partial_data_key == 'serverUsage') {
                commit("setServerUsage", { server_id: server_id, server_usage: partial_data })
            }
            resolve()
        })
    },

    /* ADD, EDIT & DELETE */
    add({ dispatch }, payload) {
        return new Promise((resolve, reject) => {
            api.add(
                payload,
                (response) => {
                    dispatch("fetchServers", {force: true, fresh: true})
                    .then(() => {
                        resolve(response)
                    })
                },
                (error) => { reject(error) }
            )
        })
    },
    edit({ dispatch }, payload) {
        return new Promise((resolve, reject) => {
            api.edit(
                payload,
                (response) => {
                    dispatch("fetchServers", {force: true, fresh: true})
                    .then(() => {
                        resolve(response)
                    })
                },
                (error) => { reject(error) }
            )
        })
    },
    delete({ dispatch }, payload) {
        return new Promise((resolve, reject) => {
            api.delete(
                payload,
                (response) => {
                    dispatch("fetchServers", {force: true, fresh: true})
                    .then(() => {
                        resolve(response)
                    })
                },
                (error) => { reject(error) }
            )
        })
    }

}

// mutations
const mutations = {
    resetState (state) {
        Object.assign(state, init_state())
    },
    setFetchingServersInProgress(state, flag) {
        state.fetching_servers_in_progress = flag
    },
    toggleShowDetails (state, index) {
        state.servers[index]._showDetails = !state.servers[index]._showDetails
    },
    setServers (state, servers) {
        Vue.set(state, 'servers', {})
        servers.forEach(server => {
            server._showDetails = false
            server._loading = false
            Vue.set(state.server_query_in_progress, server.id, false)
            Vue.set(state.server_refresh_enqueued, server.id, false)
            Vue.set(state.server_status_refresh_enqueued, server.id, false)
            Vue.set(state.server_query_error, server.id, false)
            Vue.set(state.server_status, server.id, {})
            if (server.connection_status) {
                mutations.setConnectionState(state, { server_id: server.id, connectionState: server.connection_status })
            }
            delete server.connection_status
            if (server.server_info && server.server_info.query_result !== undefined) {
                setAllQueryInfo(state, server.id, server.server_info)
                delete server.server_info.query_result
            }
            Vue.set(state.servers, server.id, server)
        })
    },
    setConnectionState(state, payload) {
        const connectionState = payload.connectionState
        let newStatus = {
            _loading: false,
            timestamp: connectionState.timestamp,
            latency: connectionState._latency,
        }
        if (connectionState.version !== undefined) {
            newStatus.data = connectionState.version
            newStatus.error = false
        } else {
            newStatus.data = connectionState.error ? connectionState.error : connectionState.message
            newStatus.error = true
        }
        state.server_status[payload.server_id] = Object.assign({}, state.server_status[payload.server_id], newStatus)
        //setUpdatableServers(state)
    },
    setServerRefreshEnqueued(state, payload) {
        const server_id = payload.server_id
        const is_enqueued = payload.is_enqueued
        state.server_refresh_enqueued[server_id] = is_enqueued
        Vue.set(state.server_query_in_progress, server_id, is_enqueued)
    },
    setServerStatusRefreshEnqueued(state, payload) {
        const server_id = payload.server_id
        const is_enqueued = payload.is_enqueued
        state.server_status_refresh_enqueued[server_id] = is_enqueued
    },
    setServerLinkTest(state, payload) {
        Vue.set(state.server_link_test, payload.server_id, {
            testing: payload.testing,
            error: payload.error || null,
            updated: Date.now(),
        })
    },
    setServerUser(state, payload) {
        if (state.server_user[payload.server_id] === undefined) {
            Vue.set(state.server_user, payload.server_id, {})
        }
        state.server_user[payload.server_id] = Object.assign({}, state.server_user[payload.server_id], payload.perms)
    },
    setRemoteConnections(state, payload) {
        if (state.remote_connections[payload.server_id] === undefined) {
            Vue.set(state.remote_connections, payload.server_id, {})
        }
        if (!Array.isArray(payload.connections)) {
            payload.connections = [payload.connections]
        }
        //const normalizedConnections = payload.connections.map(connection => {
        //    return connection
        //})
        //if (!Array.isArray(payload.connections)) {
        //    payload.connections = [{connectionTest: {status: {error: payload.connections, color: "danger"}}}]
        //}
        //state.remote_connections[payload.server_id] = Object.assign({}, state.remote_connections[payload.server_id], normalizedConnections)
        state.remote_connections[payload.server_id] = Object.assign({}, state.remote_connections[payload.server_id], payload.connections)
    },
    setSubmodules(state, payload) {
        if (state.submodules[payload.server_id] === undefined) {
            Vue.set(state.submodules, payload.server_id, {})
        }
        state.submodules[payload.server_id] = Object.assign({}, state.submodules[payload.server_id], payload.submodules)
    },
    setProxy(state, payload) {
        if (state.proxy[payload.server_id] === undefined) {
            Vue.set(state.proxy, payload.server_id, "")
        }
        Vue.set(state.proxy, payload.server_id, payload.proxy)
    },
    setZMQ(state, payload) {
        if (state.zeromq[payload.server_id] === undefined) {
            Vue.set(state.zeromq, payload.server_id, "")
        }
        Vue.set(state.zeromq, payload.server_id, payload.zmq)
    },
    setWorkers(state, payload) {
        if (state.workers[payload.server_id] === undefined) {
            Vue.set(state.workers, payload.server_id, {})
        }
        state.workers[payload.server_id] = Object.assign({}, state.workers[payload.server_id], payload.workers)
    },
    setLastRefresh(state, payload) {
        if (state.last_refresh[payload.server_id] === undefined) {
            Vue.set(state.last_refresh, payload.server_id, "")
        }
        Vue.set(state.last_refresh, payload.server_id, payload.last_refresh)
    },
    setFullInfo(state, { server_id, timestamp }) {
        Vue.set(state.full_info, server_id, timestamp)
    },
    // A light snapshot (lists) carries only the settings lists read: they update the map, the full list stays as is
    setFinalSettings(state, payload) {
        if (payload.final_settings === undefined) {
            payload.final_settings = []
        }
        if (!payload.light) {
            Vue.set(state.raw_final_settings, payload.server_id, Object.assign({}, payload.final_settings))
        }
        // create a mapping with setting-name->value
        if (state.final_settings[payload.server_id] === undefined) {
            Vue.set(state.final_settings, payload.server_id, {})
        }
        let fs = {}
        if (payload.final_settings.map(finalSetting => { return {setting: finalSetting.setting, value: finalSetting.value} })) {
            payload.final_settings.forEach(finalSetting => {
                fs[finalSetting.setting] = finalSetting.value
            })
        }
        state.final_settings[payload.server_id] = Object.assign({}, state.final_settings[payload.server_id], fs)
    },
    setServerUsage(state, payload) {
        if (state.server_usage[payload.server_id] === undefined) {
            Vue.set(state.server_usage, payload.server_id, {})
        }
        state.server_usage[payload.server_id] = Object.assign({}, state.server_usage[payload.server_id], payload.server_usage)
    },
    // Only full snapshots carry the diagnostics: each one replaces the previous
    setDiagnosticFull(state, payload) {
        Vue.set(state.diagnostic_full, payload.server_id, Object.assign({}, payload.diagnostic_full))
    },
    updateUsers(state, { server_id, users }) {
        // The whole list: users deleted on the instance must disappear
        Vue.set(state.server_users, server_id, Array.isArray(users) ? users : [])
    },
}

function setAllQueryInfo(state, server_id, server_info) {
    const query_info = server_info.query_result
    if (query_info["serverUser"])
        mutations.setServerUser(state, { server_id: server_id, perms: query_info["serverUser"] })
    if (query_info["connectedServers"])
        mutations.setRemoteConnections(state, { server_id: server_id, connections: query_info["connectedServers"] })
    if (query_info["serverSettings"]) {
        mutations.setSubmodules(state, { server_id: server_id, submodules: query_info["serverSettings"]["moduleStatus"] })
        mutations.setProxy(state, { server_id: server_id, proxy: query_info["serverSettings"]["proxyStatus"] })
        mutations.setZMQ(state, { server_id: server_id, zmq: query_info["serverSettings"]["zmqStatus"] })
        mutations.setWorkers(state, { server_id: server_id, workers: query_info["serverSettings"]["workers"] })
        mutations.setFinalSettings(state, { server_id: server_id, final_settings: query_info["serverSettings"]["finalSettings"], light: server_info.light === true })
        if (server_info.light !== true) {
            mutations.setDiagnosticFull(state, { server_id: server_id, diagnostic_full: query_info["serverSettings"] })
        }
    }
    if (server_info["timestamp"])
        mutations.setLastRefresh(state, { server_id: server_id, last_refresh: server_info["timestamp"] })
    if (query_info["serverUsage"])
        mutations.setServerUsage(state, { server_id: server_id, server_usage: query_info["serverUsage"] })
}

function commitAllQueryInfo(commit, server_id, info) {
    const queryResult = info["query_result"]
    if (queryResult["serverUser"])
        commit("setServerUser", { server_id: server_id, perms: queryResult["serverUser"] })
    if (queryResult["connectedServers"])
        commit("setRemoteConnections", { server_id: server_id, connections: queryResult["connectedServers"] })
    if (queryResult["serverSettings"]) {
        commit("setSubmodules", { server_id: server_id, submodules: queryResult["serverSettings"]["moduleStatus"] })
        commit("setProxy", { server_id: server_id, proxy: queryResult["serverSettings"]["proxyStatus"] })
        commit("setZMQ", { server_id: server_id, zmq: queryResult["serverSettings"]["zmqStatus"] })
        commit("setWorkers", { server_id: server_id, workers: queryResult["serverSettings"]["workers"] })
        commit("setFinalSettings", { server_id: server_id, final_settings: queryResult["serverSettings"]["finalSettings"], light: info.light === true })
        if (info.light !== true) {
            commit("setDiagnosticFull", { server_id: server_id, diagnostic_full: queryResult["serverSettings"] })
        }
    }
    if (info["timestamp"])
        commit("setLastRefresh", { server_id: server_id, last_refresh: info["timestamp"] })
    if (queryResult["serverUsage"])
        commit("setServerUsage", { server_id: server_id, server_usage: queryResult["serverUsage"] })
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
