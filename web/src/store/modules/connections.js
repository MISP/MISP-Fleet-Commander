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
    },
    getConnectionList: state => {
        return state.all
    },
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
    },
    editRemoteConnection({ dispatch }, payload) {
        return new Promise((resolve, reject) => {
            const server_id = payload.server_id
            const remote_server_id = payload.remote_server_id
            const payload_to_send = payload.payload
            api.editRemoteConnection(
                server_id, remote_server_id, payload_to_send,
                (response) => {
                    helpers.reloadServerConnectionList(dispatch, resolve, server_id, remote_server_id)
                },
                (error) => { reject(error) }
            )
        })
    },
    savePushRules({ dispatch }, payload) {
        return new Promise((resolve, reject) => {
            const server_id = payload.server_id
            const remote_server_id = payload.remote_server_id
            const payload_to_send = payload.payload
            api.setPushRules(
                server_id, remote_server_id, payload_to_send,
                connection => {
                    helpers.reloadServerConnectionList(dispatch, resolve, server_id, remote_server_id)
                },
                (error) => { reject(error) }
            )
        })
    },
    savePullRules({ dispatch }, payload) {
        return new Promise((resolve, reject) => {
            const server_id = payload.server_id
            const remote_server_id = payload.remote_server_id
            const payload_to_send = payload.payload
            api.setPullRules(
                server_id, remote_server_id, payload_to_send,
                connection => {
                    helpers.reloadServerConnectionList(dispatch, resolve, server_id, remote_server_id)
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
    setConnections(state, connections) {
        state.all = connections
    },
    setConnection(state, connection) {
        for (let i = 0; i < state.all.length; i++) {
            if (state.all[i].vid == connection.vid) {
                Vue.set(state.all, i, connection)
                break
            }
        }
    },
}

const helpers = {
    reloadServerConnectionList(dispatch, resolve, server_id, remote_server_id) {
        const fakeConnectionForAPI = {
            source: {id: server_id},
            destination: {Server: {id: remote_server_id}}
        }
        dispatch("getConnection", fakeConnectionForAPI).then(() => {
            resolve()
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
