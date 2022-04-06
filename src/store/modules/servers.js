import api from "@/api/servers"
import Vue from "vue"

// initial state
const init_state = () => {
    return {
        githubVersion: "",
        servers: {},
        server_status: {},
        server_query_in_progress: {},
        server_query_error: {},
        user_perms: {},
        remote_connections: {},
        submodules: {},
        proxy: {},
        zeromq: {},
        workers: {},
        serverUsers: {},
        last_refresh: {},
        diagnostic_full: {},
    }
}

const state = init_state()

// getters
const getters = {
    serverCount: state => {
        return state.servers.length
    },
    getServerList: state => {
        return Object.values(state.servers)
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
                api.index(servers => {
                        commit("setServers", servers)
                        resolve()
                    },
                    (error) => { reject(error) }
                )
            } else {
                resolve("Server already loaded")
            }
        })
    },
    runConnectionTest({ commit, state }, server_id) {
        return new Promise((resolve, reject) => {
            commit("resetConnectionState", { server_id: server_id })
            api.testConnection(
                state.servers[server_id],
                connectionState => {
                    commit("setConnectionState", { server_id: server_id, connectionState: connectionState })
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    runAllConnectionTest({ commit }) {
        return new Promise((resolve, reject) => {
            commit("resetConnectionsState")
            api.batchTestConnection(
                connectionsState => {
                    connectionsState.forEach(connection => {
                        commit("setConnectionState", { server_id: connection.server_id, connectionState: connection })
                    })
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    runSelectedConnectionTest({ dispatch }, payload) {
        return new Promise((resolve, reject) => {
            payload.selection.forEach(server_id => {
                dispatch("runConnectionTest", server_id)
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        reject(error)
                    })
            })
        })
    },
    fetchServerInfo({ commit }, payload) {
        return new Promise((resolve, reject) => {
            commit("updateQueryState", { server_id: payload.server_id, loading: true })
            api.queryInfo(
                payload,
                (info) => {
                    commit("updateQueryState", { server_id: payload.server_id, info: info, loading: false })
                    commitAllQueryInfo(commit, payload.server_id, info)
                    resolve()
                },
                (error) => {
                    commit("updateQueryState", { server_id: payload.server_id, loading: false })
                    commitAllQueryInfo(commit, payload.server_id)
                    reject(error)
                }
            )
        })
    },
    fetchAllServerInfo({ getters, commit }) {
        return new Promise((resolve, reject) => {
            getters.getServerList.forEach(server => {
                dispatch("fetchServerInfo", { server: server, no_cache: payload.no_cache })
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        reject(error)
                    })
            })
        })
    },
    fetchSelectedServerInfo({ state, dispatch }, payload) {
        return new Promise((resolve, reject) => {
            payload.selection.forEach(server_id => {
                dispatch("fetchServerInfo", { server: state.servers[server_id], no_cache: payload.no_cache })
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        reject(error)
                    })
            })
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
    fetchGithubVersion({ commit }) {
        return new Promise((resolve, reject) => {
            api.fetchGithubVersion(
                (githubReply) => {
                    commit("setGithubVersion", githubReply)
                    resolve()
                },
                (error) => { 
                    reject(error)
                }
            )
        })
    },

    /* ADD, EDIT & DELETE */
    add(payload) {
        return new Promise((resolve, reject) => {
            api.add(
                payload,
                () => {
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    edit(payload) {
        return new Promise((resolve, reject) => {
            api.edit(
                payload,
                () => {
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    delete(payload) {
        return new Promise((resolve, reject) => {
            api.delete(
                payload,
                () => {
                    resolve()
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
    toggleShowDetails (state, index) {
        state.servers[index]._showDetails = !state.servers[index]._showDetails
    },
    setServers (state, servers) {
	Object.assign(state.servers, {})
        servers.forEach(server => {
            server._showDetails = false
            server._loading = false
            server.canBeUpdated = false
            Vue.set(state.server_query_in_progress, server.id, false)
            Vue.set(state.server_query_error, server.id, false)
            Vue.set(state.server_status, server.id, {})
            if (server.server_info.query_result !== undefined) {
                setAllQueryInfo(state, server.id, server.server_info)
                delete server.server_info.query_result
            }
            Vue.set(state.servers, server.id, server)
        })
    },
    resetConnectionState(state, payload) {
        Vue.set(state.server_status, payload.server_id, {_loading: true})
    },
    resetConnectionsState(state) {
        Object.values(state.servers).forEach(server => {
            Vue.set(state.server_status, server.id, {_loading: true})
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
            newStatus = connectionState.error
            newStatus.error = true
        }
        state.server_status[payload.server_id] = Object.assign({}, state.server_status[payload.server_id], newStatus)
        setUpdatableServers(state)
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
    setUserPerms(state, payload) {
        if (state.user_perms[payload.server_id] === undefined) {
            Vue.set(state.user_perms, payload.server_id, {})
        }
        state.user_perms[payload.server_id] = Object.assign({}, state.user_perms[payload.server_id], payload.perms)
    },
    setRemoteConnections(state, payload) {
        if (state.remote_connections[payload.server_id] === undefined) {
            Vue.set(state.remote_connections, payload.server_id, {})
        }
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
    setDiagnosticFull(state, payload) {
        if (state.diagnostic_full[payload.server_id] === undefined) {
            Vue.set(state.diagnostic_full, payload.server_id, {})
        }
        //state.diagnostic_full[payload.server_id] = Object.assign({}, state.diagnostic_full[payload.server_id], payload.diagnostic_full)
    },
    updateUsers(state, { server_id, users }) {
        if (state.serverUsers[server_id] === undefined) {
            Vue.set(state.serverUsers, server_id, {})
        }
        state.serverUsers[server_id] = Object.assign({}, state.serverUsers[server_id], users)
    },
    setGithubVersion(state, githubReply) {
        const githubVersion = githubReply.tag_name
        state.githubVersion = githubVersion
        setUpdatableServers(state)
    }
}

function setAllQueryInfo(state, server_id, server_info) {
    const query_info = server_info.query_result
    mutations.setUserPerms(state, { server_id: server_id, perms: query_info["serverUser"]["Role"] })
    mutations.setRemoteConnections(state, { server_id: server_id, connections: query_info["connectedServers"] })
    mutations.setSubmodules(state, { server_id: server_id, submodules: query_info["serverSettings"]["moduleStatus"] })
    mutations.setProxy(state, { server_id: server_id, proxy: query_info["serverSettings"]["proxyStatus"] })
    mutations.setZMQ(state, { server_id: server_id, zmq: query_info["serverSettings"]["zmqStatus"] })
    mutations.setWorkers(state, { server_id: server_id, workers: query_info["serverSettings"]["workers"] })
    mutations.setLastRefresh(state, { server_id: server_id, last_refresh: server_info["timestamp"] })
    mutations.setDiagnosticFull(state, { server_id: server_id, diagnostic_full: query_info["serverSettings"] })
}

function commitAllQueryInfo(commit, server_id, info) {
    commit("setUserPerms", { server_id: server_id, perms: info["serverUser"]["Role"] })
    commit("setRemoteConnections", { server_id: server_id, connections: info["connectedServers"] })
    commit("setSubmodules", { server_id: server_id, submodules: info["serverSettings"]["moduleStatus"] })
    commit("setProxy", { server_id: server_id, proxy: info["serverSettings"]["proxyStatus"] })
    commit("setZMQ", { server_id: server_id, zmq: info["serverSettings"]["zmqStatus"] })
    commit("setWorkers", { server_id: server_id, workers: info["serverSettings"]["workers"] })
    commit("setLastRefresh", { server_id: server_id, last_refresh: info["timestamp"] })
    commit("setDiagnosticFull", { server_id: server_id, diagnostic_full: info["serverSettings"] })
}

function setUpdatableServers(state) {
    Object.values(state.servers).forEach(server => {
        server.canBeUpdated = canBeUpdated(state, server)
    })
}

function canBeUpdated(state, server) {
    const githubVersion = state.githubVersion
    if (githubVersion !== "" && githubVersion !== undefined) {
        const server_status = state.server_status[server.id]
        if (server_status !== undefined && server_status.data !== undefined) {
            const parsedGithubVersion = tokenizeMISPVersion(githubVersion)
            const parsedServerVersion = tokenizeMISPVersion(server_status.data)
            if (parsedGithubVersion.major !== parsedServerVersion.major) {
                return false // update for major version should be done manually
            } else if (parsedGithubVersion.minor !== parsedServerVersion.minor) {
                return false // update for major version should be done manually
            } else if (parsedGithubVersion.patch > parsedServerVersion.patch) {
                return true
            } else {
                return false
            }
        }
    }
    return false
}
function tokenizeMISPVersion(versionString) {
    let version = {}
    if (versionString !== "" && versionString !== undefined) {
        if (versionString.startsWith("v")) {
            versionString = versionString.slice(1)
        }
        let arr = versionString.split(".")
        version = {major: arr[0], minor: arr[1], patch: arr[2]}
    }
    return version
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
