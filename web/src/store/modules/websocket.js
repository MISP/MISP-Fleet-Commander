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
    SOCKET_DOACTION({ commit }, message) {
        console.log('wsaction ' + message);
        Vue.prototype.$socket.emit('xname2', 'test-from-client')
    },
    SOCKET_UPDATE_SERVER({ dispatch }, serverData) {
        if (serverData.server.server_group.id == store.getters["serverGroups/selectedServerGroup"].id)  {
            dispatch("servers/commitAllQueryInfo", serverData, { root: true })
        }
    },
    SOCKET_SERVER_UPDATING({ commit }, serverData) {
        const payload = {
            server_id: serverData,
            is_enqueued: true,
        }
        commit("servers/setServerRefreshEnqueued", payload, { root: true })
    },
}

// mutations
const mutations = {
    setConnected: function (state, connectionState) {
        state.isConnected = connectionState;
    },
    SOCKET_UPDATE(state, message) {
        console.log('wsmutation  ' + message);
    }
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
