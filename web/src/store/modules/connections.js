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
    // server_id -> {total, unused, ok, degraded, broken, unknown, worst}: health of the server's outgoing links.
    // Unused links are counted apart: nothing depends on them
    linkHealthBySource: state => {
        const bySource = {}
        state.all.forEach(link => {
            const sourceID = link.source && link.source.id
            if (sourceID === undefined) {
                return
            }
            const entry = bySource[sourceID] || (bySource[sourceID] = { ...emptyLinkCounts(), worst: null })
            entry.total += 1
            if (link.health && link.health.disabled) {
                entry.unused += 1
            } else {
                entry[(link.health && link.health.level) || "unknown"] += 1
            }
        })
        Object.values(bySource).forEach(entry => {
            entry.worst = LINK_LEVELS.find(level => entry[level] > 0) || null
        })
        return bySource
    },
}

// Most severe first
export const LINK_LEVELS = ["broken", "degraded", "unknown", "ok"]

export function emptyLinkCounts() {
    return { total: 0, unused: 0, ok: 0, degraded: 0, broken: 0, unknown: 0 }
}

export function isProblemLink(link) {
    const health = link.health || {}
    return !health.disabled && (health.level === "broken" || health.level === "degraded")
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
    toggleShowDetails (state, connection) {
        const target = state.all.find(c => c.vid == connection.vid)
        if (target !== undefined) {
            Vue.set(target, '_showDetails', !target._showDetails)
        }
    },
    setConnections(state, connections) {
        state.all = connections
    },
    setConnection(state, connection) {
        for (let i = 0; i < state.all.length; i++) {
            if (state.all[i].vid == connection.vid) {
                // keep the row expanded when its data is refreshed
                connection._showDetails = state.all[i]._showDetails
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
