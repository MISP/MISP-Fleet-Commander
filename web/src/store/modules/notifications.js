import api from "@/api/notifications"

// initial state
const state = {
    all: []
}

// getters
const getters = {}

// actions
const actions = {
    getNotifications({ commit }, server_id) {
        return new Promise((resolve, reject) => {
            api.get(
                server_id,
                notifications => {
                    commit("setNotifications", notifications)
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
}

// mutations
const mutations = {
    setNotifications(state, notifications) {
        state.all = notifications
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
