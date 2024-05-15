import api from "@/api/userSettings"

// initial state
const state = {
    all: []
}

// getters
const getters = {
    getUserSettingList: state => {
        return state.all
    },
}

// actions
const actions = {
    getUserSettings({ commit }, payload={}) {
        return new Promise((resolve, reject) => {
            api.index(
                userSettings => {
                    commit("setUserSettings", userSettings)
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    add({ commit }, payload) {
        return new Promise((resolve, reject) => {
            api.add(
                payload,
                () => {
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    edit({ commit }, payload) {
        return new Promise((resolve, reject) => {
            api.edit(
                payload,
                () => {
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    delete({ commit }, user_id) {
        return new Promise((resolve, reject) => {
            api.delete(
                user_id,
                () => {
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
}

// mutations
const mutations = {
    setUserSettings(state, userSettings) {
        state.all = userSettings
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
