import api from "@/api/servers"

// initial state
const state = {
    githubVersion: "",
    all: [],
    idToServer: {}
}

// getters
const getters = {
    serverCount: state => {
        return state.all.length
    }
}

// actions
// API Usage: api.[action]({parameters}, callback, errorCallback)
const actions = {

    /* FETCH */
    getAllServers({ commit }) {
        // this function should not fetch data if it has been fetched already
        return new Promise((resolve, reject) => {
            api.index(
                servers => {
                    servers.forEach(server => {
                        server.status = { _loading: false }
                        if (server.server_info === null) {
                            server.server_info = {query_result: {}, error: null, _loading: false}
                        } else {
                            server.server_info._loading = false
                        }
                        server._showDetails = false
                        server._loading = false
                    })
                    commit("setServers", servers)
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    refreshConnectionState({ commit }, server) {
        return new Promise((resolve, reject) => {
            commit("resetConnectionState", { server_id: server.id })
            api.testConnection(
                server,
                connectionState => {
                    commit("updateConnectionState", { server_id: server.id, connectionState: connectionState})
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    refreshAllConnectionState({ commit }) {
        return new Promise((resolve, reject) => {
            commit("resetConnectionsState")
            api.batchTestConnection(
                connectionsState => {
                    commit("updateConnectionsState", { connectionsState: connectionsState})
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    refreshSelectedConnectionState({ dispatch }, payload) {
        return new Promise((resolve, reject) => {
            payload.selection.forEach(server => {
                dispatch("refreshConnectionState", server)
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        reject(error)
                    })
            })
        })
    },
    getInfo({ commit }, payload) {
        return new Promise((resolve, reject) => {
            commit("updateInfo", { server_id: payload.server.id, loading: true }) // try to only change loading and not replace the info field? create a new mutation `updateLoading`
            api.queryInfo(
                payload,
                (info) => {
                    commit("updateInfo", { server_id: payload.server.id, info: info, loading: false})
                    resolve()
                },
                (error) => { 
                    commit("updateInfo", { server_id: payload.server.id, loading: false })
                    reject(error)
                }
            )
        })
    },
    getAllInfo({ state, dispatch }, payload) {
        return new Promise((resolve, reject) => {
            state.all.forEach(server => {
                dispatch("getInfo", {server: server, no_cache: payload.no_cache})
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        reject(error)
                    })
            })
        })
    },
    getSelectedInfo({ dispatch }, payload) {
        return new Promise((resolve, reject) => {
            payload.selection.forEach(server => {
                dispatch("getInfo", {server: server, no_cache: payload.no_cache})
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        reject(error)
                    })
            })
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
    add(context, payload) {
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
    delete(context, payload) {
        return new Promise((resolve, reject) => {
            api.delete(
                payload,
                () => {
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },

}

// mutations
const mutations = {
    toggleShowDetails (state, index) {
        state.all[index]._showDetails = !state.all[index]._showDetails
    },
    setServers (state, servers) {
        state.all = servers
        state.idToServer = {}
        servers.forEach(server => {
            state.idToServer[server.id] = server
        })
    },
    resetConnectionState(state, payload) {
        let server = state.idToServer[payload.server_id]
        server.status = { _loading: true }
    },
    resetConnectionsState(state) {
        state.all.forEach(server => {
            server.status = { _loading: true }
        })
    },
    updateConnectionState(state, payload) {
        let server = state.idToServer[payload.server_id]
        const connection = payload.connectionState
        if (connection.version !== undefined) {
            server.status = { _loading: false, data: connection.version, error: false }
        } else {
            server.status = { _loading: false, data: connection.error, error: true }
        }
        setUpdatableServers(state)
    },
    updateConnectionsState(state, payload) {
        const connectionsState = payload.connectionsState
        connectionsState.forEach(connection => {
            let server = state.all.find(server => server.id == connection.server_id)
            if (connection.version !== undefined) {
                server.status = { _loading: false, data: connection.version, error: false }
            } else {
                server.status = { _loading: false, data: connection.error, error: true }
            }
        })
        setUpdatableServers(state)
    },
    updateInfo(state, payload) {
        let server = state.idToServer[payload.server_id]
        server._loading = payload.loading
        server.server_info._loading = payload.loading
        const info = payload.info
        if (info !== undefined) {
            if (info.error === undefined) {
                server.server_info = Object.assign({}, server.server_info, info) // update information keeping the observers
                server.server_info.error = false
            } else {
                server.server_info.error = info.error
                server.server_info.error = true
            }
        }
    },
    setGithubVersion(state, githubReply) {
        // const githubVersion = githubReply.tag_name
        const githubVersion = "v2.4.123"
        state.githubVersion = githubVersion
        setUpdatableServers(state)
    }
}

function setUpdatableServers(state) {
    state.all.forEach(server => {
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