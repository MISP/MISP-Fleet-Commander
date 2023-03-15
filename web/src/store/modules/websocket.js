import Vue from "vue"

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
        console.log('connected');
        commit("setConnected", true)
    },
    SOCKET_DISCONNECT(state) {
        console.log('dis-connected');
        commit("setConnected", false)
    },
    SOCKET_DOACTION({ commit }, message) {
        console.log('wsaction ' + message);
        Vue.prototype.$socket.emit('xname2', 'test-from-client')
    },
    SOCKET_UPDATE_SERVER({ commit }, serverData) {
        console.log(serverData);
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
