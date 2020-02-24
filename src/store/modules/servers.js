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
    getAllServers ({ commit }) {
        // this function should not fetch data if it has been fetched already
        return new Promise((resolve, reject) => {
            api.index(
                servers => {
                    servers.forEach(server => {
                        server.status = {}
                        server.diagnostic = {}
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
    }
}

// mutations
const mutations = {
    setServers (state, servers) {
        state.all = servers
    },
    updateConnectionState(state, payload) {
        state.all.forEach(server => {
            if (server.id == payload.server_id) {
                const connection = payload.connectionState
                if (connection.version !== undefined) {
                    server.status = { message: connection.version, error: false }
                } else {
                    server.status = { message: connection.error, error: true }
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