import Vue from "vue"
import store from "@/store/index"

// initial state
const state = {
    isConnected: false,
}

// getters
const getters = {
    wsConnected: state => {
        return state.isConnected
    },
}

// actions
const actions = {
    SOCKET_CONNECT(state) {
        commit("setConnected", true)
    },
    SOCKET_DISCONNECT(state) {
        commit("setConnected", false)
    },
    SOCKET_PONG({ dispatch }, okState) {
        dispatch("ui/setWorkerHealthStatus", okState.ok, { root: true })
    },
    SOCKET_UPDATE_SERVER({ dispatch }, serverData) {
        if (store.getters["fleets/selectedFleet"] === null) {
            return
        }
        if (serverData.server.fleet.id == store.getters["fleets/selectedFleet"].id)  {
            dispatch("servers/commitAllQueryInfo", serverData, { root: true })
        }
    },
    SOCKET_UPDATE_SERVER_CONNECTION({ dispatch }, serverData) {
        if (store.getters["fleets/selectedFleet"] === null) {
            return
        }
        if (serverData.server.fleet.id == store.getters["fleets/selectedFleet"].id)  {
            dispatch("servers/commitConnectionTestInfo", serverData, { root: true })
        }
    },
    SOCKET_UPDATE_SERVER_PARTIAL_DATA({ dispatch }, payload) {
        if (store.getters["fleets/selectedFleet"] === null) {
            return
        }
        if (payload.server.fleet.id == store.getters["fleets/selectedFleet"].id)  {
            dispatch("servers/commitPartialServerData", payload, { root: true })
        }
    },
    SOCKET_SERVER_UPDATING({ commit }, serverData) {
        const payload = {
            server_id: serverData,
            is_enqueued: true,
        }
        commit("servers/setServerRefreshEnqueued", payload, { root: true })
    },
    SOCKET_SERVER_STATUS_UPDATING({ commit }, serverData) {
        const payload = {
            server_id: serverData,
            is_enqueued: true,
        }
        commit("servers/setServerStatusRefreshEnqueued", payload, { root: true })
    },
    SOCKET_SERVER_GRAPHS_UPDATING({ commit }, serverData) {
        const payload = {
            server_id: serverData,
            is_enqueued: true,
        }
        commit("servers/setServerGraphsRefreshEnqueued", payload, { root: true })
    },
    SOCKET_SERVER_GRAPHS_UPDATE_DONE({ commit }, serverData) {
        const payload = {
            server_id: serverData,
            is_enqueued: false,
        }
        commit("servers/setServerGraphsRefreshEnqueued", payload, { root: true })
    },
    SOCKET_FLEET_UPDATE_TIMESTAMPS({ commit }, fleetData) {
        const payload = { fleet_id: fleetData.fleet_id }
        if (fleetData.watched_timestamp)
            payload.watched_timestamp = fleetData.watched_timestamp
        if (fleetData.monitored_timestamp)
            payload.monitored_timestamp = fleetData.monitored_timestamp
        commit("fleets/setFleetTimestamps", payload, { root: true })
    },
}

// mutations
const mutations = {
    setConnected: function (state, connectionState) {
        state.isConnected = connectionState;
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
