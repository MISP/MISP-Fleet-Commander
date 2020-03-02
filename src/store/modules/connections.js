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
    }
}

// mutations
const mutations = {
    setConnections(state, connections) {
        state.all = connections
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
