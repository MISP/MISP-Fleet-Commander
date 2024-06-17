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
    SOCKET_UPDATE_SERVER({ dispatch }, serverData) {
        if (serverData.server.fleet.id == store.getters["fleets/selectedFleet"].id)  {
            dispatch("servers/commitAllQueryInfo", serverData, { root: true })
        }
    },
    SOCKET_UPDATE_SERVER_CONNECTION({ dispatch }, serverData) {
        if (serverData.server.fleet.id == store.getters["fleets/selectedFleet"].id)  {
            dispatch("servers/commitConnectionTestInfo", serverData, { root: true })
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
