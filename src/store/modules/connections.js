import api from "@/api/connections"

// initial state
const state = {
    all: []
}

// getters
const getters = {}

// actions
const actions = {
    getConnections({ commit }) {
        return new Promise((resolve, reject) => {
            api.index(
                connections => {
                    connections.forEach(connection => {
                        connection._loading = false
                    })
                    commit("setConnections", connections)
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    getConnection({ commit }, data) {
        return new Promise((resolve, reject) => {
            api.get(
                connection => {
                    commit("setConnection", connection)
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    }
}

// mutations
const mutations = {
    setConnections(state, connections) {
        state.all = connections
    },
    setConnection(state, connection) {
        let i = 0
        state[i] = connection
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
