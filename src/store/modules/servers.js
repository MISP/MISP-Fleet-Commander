import api from "@/api/servers"

// initial state
const state = {
    githubVersion: "",
    severs: {},
    status: {},
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

// getters
const getters = {
    serverCount: state => {
        return state.all.length
    },
    getServerList: state => {
        return Object.values(state.servers)
    },
}

// actions
// API Usage: api.[action]({parameters}, callback, errorCallback)
const actions = {

    fetchServers({ commit }, payload) {
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
                    setAllQueryInfo(commit, payload.server_id, info)
                    resolve()
                },
                (error) => {
                    commit("updateQueryState", { server_id: payload.server_id, loading: false })
                    setAllQueryInfo(commit, payload.server_id)
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
    toggleShowDetails (state, index) {
        state.all[index]._showDetails = !state.all[index]._showDetails
    },
    setServers (state, servers) {
        servers.forEach(server => {
            server._showDetails = false
            server._loading = false
            server.canBeUpdated = false
            server.status = {}
            state.servers[server.id] = server
            state.server_query_in_progress[server.id] = false
            state.server_query_error[server.id] = false
        })
    },
    resetConnectionState(state, payload) {
        Vue.set(state.servers[payload.server_id].status, '_loading', true)
    },
    resetConnectionsState(state) {
        Object.values(state.servers).forEach(server => {
            Vue.set(server.status, '_loading', true)
        })
    },
    setConnectionState(state, payload) {
        let server = state.servers[payload.server_id]
        const connection = payload.connectionState
        let newStatus = {
            _loading: false,
            timestamp: connection.timestamp,
        }
        if (connection.version !== undefined) {
            newStatus.data = connection.version
            newStatus.error = false
        } else {
            newStatus = connection.error
            newStatus.error = true
        }
        server.status = Object.assign({}, server.status, newStatus)
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
            Vue.set(state.proxy, payload.server_id, {})
        }
        state.proxy[payload.server_id] = Object.assign({}, state.proxy[payload.server_id], payload.proxy)
    },
    setZMQ(state, payload) {
        if (state.zeromq[payload.server_id] === undefined) {
            Vue.set(state.zeromq, payload.server_id, {})
        }
        state.zeromq[payload.server_id] = Object.assign({}, state.zeromq[payload.server_id], payload.zmq)
    },
    setWorkers(state, payload) {
        if (state.workers[payload.server_id] === undefined) {
            Vue.set(state.workers, payload.server_id, {})
        }
        state.workers[payload.server_id] = Object.assign({}, state.workers[payload.server_id], payload.workers)
    },
    setLastRefresh(state, payload) {
        if (state.last_refresh[payload.server_id] === undefined) {
            Vue.set(state.last_refresh, payload.server_id, {})
        }
        state.last_refresh[payload.server_id] = Object.assign({}, state.last_refresh[payload.server_id], payload.last_refresh)
    },
    setDiagnosticFull(state, payload) {
        if (state.diagnostic_full[payload.server_id] === undefined) {
            Vue.set(state.diagnostic_full, payload.server_id, {})
        }
        state.diagnostic_full[payload.server_id] = Object.assign({}, state.diagnostic_full[payload.server_id], payload.diagnostic_full)
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

function setAllQueryInfo(commit, server_id, info) {
    commit("setUserPerms", { server_id: server_id, perms: info["serverUser"] })
    commit("setRemoteConnections", { server_id: server_id, perms: info["connectedServers"] })
    commit("setSubmodules", { server_id: server_id, perms: info["serverSettings"]["moduleStatus"] })
    commit("setProxy", { server_id: server_id, perms: info["serverSettings"]["proxyStatus"] })
    commit("setZMQ", { server_id: server_id, perms: info["serverSettings"]["zmqStatus"] })
    commit("setWorkers", { server_id: server_id, perms: info["serverSettings"]["workers"] })
    commit("setLastRefresh", { server_id: server_id, perms: info["timestamp"] })
    commit("setDiagnosticFull", { server_id: server_id, perms: info["serverSettings"] })
}

function setUpdatableServers(state) {
    Object.values(state.servers).forEach(server => {
        server.canBeUpdated = canBeUpdated(state, server)
    })
}

function canBeUpdated(state, server) {
    const githubVersion = state.githubVersion
    if (githubVersion !== "" && githubVersion !== undefined) {
        if (server.status.data !== undefined) {
            const parsedGithubVersion = tokenizeMISPVersion(githubVersion)
            const parsedServerVersion = tokenizeMISPVersion(server.status.data)
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
