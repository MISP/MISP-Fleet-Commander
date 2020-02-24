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
                        server.diagnostic = {}
                        server._showDetails = false
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
    getDiagnostic({ commit }, server) {
        return new Promise((resolve, reject) => {
            commit("updateDiagnostic", { server_id: server.id, diagnostic: { loading: true }})
            api.queryDiagnostic(
                server,
                diagnostic => {
                    commit("updateDiagnostic", { server_id: server.id, diagnostic: diagnostic})
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
        state.all[index].diagnostic.loading = !state.all[index].diagnostic.loading
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
    updateDiagnostic(state, payload) {
        state.all.forEach(server => {
            if (server.id == payload.server_id) {
                const diagnostic = payload.diagnostic
                if (diagnostic.error === undefined) {
                    server.diagnostic = { data: diagnostic, error: false }
                } else {
                    server.diagnostic = { data: diagnostic.error, error: true }
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