import api from "@/api/servers"

// initial state
const state = {
    all: []
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
    getAllServers({ commit }) {
        // this function should not fetch data if it has been fetched already
        return new Promise((resolve, reject) => {
            api.index(
                servers => {
                    servers.forEach(server => {
                        server.status = {}
                        if (server.server_info === undefined || server.server_info === null) {
                            server.server_info = {data: {}, error: null}
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
    refreshAllConnectionState({state, dispatch}) {
        let promises = []
        state.all.forEach(server => {
            promises.push(dispatch("refreshConnectionState", server))
        })
        return Promise.all(promises)
    },
    getInfo({ commit }, payload) {
        return new Promise((resolve, reject) => {
            // commit("updateInfo", { server_id: payload.server.id, info: {}, loading: true })
            commit("updateInfo", { server_id: payload.server.id, loading: true }) // try to only change loading and not replace the info field? create a new mutation `updateLoading`
            api.queryInfo(
                payload,
                (info) => {
                    commit("updateInfo", { server_id: payload.server.id, info: info, loading: false})
                    resolve()
                },
                (error) => { 
                    // commit("updateInfo", { server_id: payload.server.id, loading: true })
                    reject(error)
                }
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
        state.all = servers
    },
    updateConnectionState(state, payload) {
        state.all.forEach(server => {
            if (server.id == payload.server_id) {
                const connection = payload.connectionState
                if (connection.version !== undefined) {
                    server.status = { data: connection.version, error: false }
                } else {
                    server.status = { data: connection.error, error: true }
                }
            }
        })
    },
    updateInfo(state, payload) {
        state.all.forEach(server => {
            if (server.id == payload.server_id) {
                server._loading = payload.loading
                const info = payload.info
                if (info !== undefined) {
                    if (info.error === undefined) {
                        server.server_info.data = info
                        // For an unkwown reason, when the server get update after fetching the server query, the update is not propageted to the badge component
                        // this.$set(server.server_info, "data", info)
                        // server.server_info.data = Object.assign({}, server.server_info.data, info)
                        server.server_info.error = false
                    } else {
                        server.server_info.data = info.error
                        server.server_info.error = true
                    }
                }
            }
        })
    }
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}