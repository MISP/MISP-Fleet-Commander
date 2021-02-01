import api from "@/api/connections"
import Vue from "vue"

// initial state
const state = {
    all: []
}

// getters
const getters = {
    connectionCount: state => {
        return state.all.length
    }
}

// actions
const actions = {
    getConnections({ commit }, payload={}) {
        return new Promise((resolve, reject) => {
            if (payload.init_only && getters.connectionCount > 0) {
                resolve("Server already loaded")
            } else {
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
            }
        })
    },
    getConnection({ commit }, payload={}) {
        return new Promise((resolve, reject) => {
            api.get(
                payload,
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
    toggleShowDetails (state, index) {
        state.all[index]._showDetails = !state.all[index]._showDetails
    },
    setConnections(state, connections) {
        state.all = connections
    },
    setConnection(state, connection) {
        for (let i = 0; i < state.all.length; i++) {
            if (state.all[i].vid == connection.vid) {
                const updatedConnection = state.all[i] = {...state.all[i], connection}
                Vue.set(state.all, i, updatedConnection)
                break
            }
        }
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
