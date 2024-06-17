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
    }
}

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
            const server_uuid = state.final_settings[server.id]['MISP.uuid']
            serversByUUID[server_uuid] = server
        })
        return serversByUUID
    },
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
    fetchServers({ commit }, payload) {
        return new Promise((resolve, reject) => {
            if (getters.serverCount == 0 || (payload !== undefined && payload.force)) {
                commit('setFetchingServersInProgress', true)
                api.index(servers => {
                        commit("setServers", servers)
                        resolve()
                    },
                    (error) => { reject(error) }
                )
                commit('setFetchingServersInProgress', false)
            } else {
                resolve("Server already loaded")
            }
        })
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
    commitAllQueryInfo({ commit }, payload) {
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

    /* ADD, EDIT & DELETE */
    add({ dispatch }, payload) {
        return new Promise((resolve, reject) => {
            api.add(
                payload,
                (response) => {
                    dispatch("fetchServers", {force: true})
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
                    dispatch("fetchServers", {force: true})
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
                    dispatch("fetchServers", {force: true})
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
            server.canBeUpdated = false
            Vue.set(state.server_query_in_progress, server.id, false)
            Vue.set(state.server_refresh_enqueued, server.id, false)
            Vue.set(state.server_status_refresh_enqueued, server.id, false)
            Vue.set(state.server_query_error, server.id, false)
            Vue.set(state.server_status, server.id, {})
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
            newStatus.data = connectionState.error
            newStatus.error = true
        }
        state.server_status[payload.server_id] = Object.assign({}, state.server_status[payload.server_id], newStatus)
        //setUpdatableServers(state)
    },
    setQueryState(state, payload) {
        let server = state.servers[payload.server_id]
        state.server_query_in_progress[payload.server_id] = payload.loading
        const info = payload.info
        if (info !== undefined) {
            if (info.error === undefined) {
                server.server_query_error = false
            } else {
                state.server_query_error = info.error ? info.error : true
            }
        }
    },
    setServerRefreshEnqueued(state, payload) {
        const server_id = payload.server_id
        const is_enqueued = payload.is_enqueued
        state.server_refresh_enqueued[server_id] = is_enqueued
    },
    setServerStatusRefreshEnqueued(state, payload) {
        const server_id = payload.server_id
        const is_enqueued = payload.is_enqueued
        state.server_status_refresh_enqueued[server_id] = is_enqueued
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
    setFinalSettings(state, payload) {
        if (payload.final_settings === undefined) {
            payload.final_settings = []
        }
        if (state.raw_final_settings[payload.server_id] === undefined) {
            Vue.set(state.raw_final_settings, payload.server_id, {})
        }
        state.raw_final_settings[payload.server_id] = Object.assign({}, state.raw_final_settings[payload.server_id], payload.final_settings)
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
    setDiagnosticFull(state, payload) {
        if (state.diagnostic_full[payload.server_id] === undefined) {
            Vue.set(state.diagnostic_full, payload.server_id, {})
        }
        state.diagnostic_full[payload.server_id] = Object.assign({}, state.diagnostic_full[payload.server_id], payload.diagnostic_full)
    },
    updateUsers(state, { server_id, users }) {
        if (state.server_users[server_id] === undefined) {
            Vue.set(state.server_users, server_id, {})
        }
        state.server_users[server_id] = Object.assign({}, state.server_users[server_id], users)
    },
}

function setAllQueryInfo(state, server_id, server_info) {
    const query_info = server_info.query_result
    mutations.setServerUser(state, { server_id: server_id, perms: query_info["serverUser"] })
    mutations.setRemoteConnections(state, { server_id: server_id, connections: query_info["connectedServers"] })
    mutations.setSubmodules(state, { server_id: server_id, submodules: query_info["serverSettings"]["moduleStatus"] })
    mutations.setProxy(state, { server_id: server_id, proxy: query_info["serverSettings"]["proxyStatus"] })
    mutations.setZMQ(state, { server_id: server_id, zmq: query_info["serverSettings"]["zmqStatus"] })
    mutations.setWorkers(state, { server_id: server_id, workers: query_info["serverSettings"]["workers"] })
    mutations.setLastRefresh(state, { server_id: server_id, last_refresh: server_info["timestamp"] })
    mutations.setServerUsage(state, { server_id: server_id, server_usage: query_info["serverUsage"] })
    mutations.setFinalSettings(state, { server_id: server_id, final_settings: query_info["serverSettings"]["finalSettings"] })
    mutations.setDiagnosticFull(state, { server_id: server_id, diagnostic_full: query_info["serverSettings"] })
}

function commitAllQueryInfo(commit, server_id, info) {
    const queryResult = info["query_result"]
    commit("setServerUser", { server_id: server_id, perms: queryResult["serverUser"] })
    commit("setRemoteConnections", { server_id: server_id, connections: queryResult["connectedServers"] })
    commit("setSubmodules", { server_id: server_id, submodules: queryResult["serverSettings"]["moduleStatus"] })
    commit("setProxy", { server_id: server_id, proxy: queryResult["serverSettings"]["proxyStatus"] })
    commit("setZMQ", { server_id: server_id, zmq: queryResult["serverSettings"]["zmqStatus"] })
    commit("setWorkers", { server_id: server_id, workers: queryResult["serverSettings"]["workers"] })
    commit("setLastRefresh", { server_id: server_id, last_refresh: info["timestamp"] })
    commit("setServerUsage", { server_id: server_id, server_usage: queryResult["serverUsage"] })
    commit("setFinalSettings", { server_id: server_id, final_settings: queryResult["serverSettings"]["finalSettings"]})
    commit("setDiagnosticFull", { server_id: server_id, diagnostic_full: queryResult["serverSettings"] })
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
