import api from "@/api/userSettings"

// initial state
const state = {
    all: [],
    all_settings: {},
    all_settings_name: {},
}

// getters
const getters = {
    getUserSettingList: state => {
        return state.all
    },
    getAllUserSettings: state => {
        return state.all_settings
    },
    getAllUserSettingsName: state => {
        return state.all_settings_name
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
    editForUser({ }, payload) {
        return new Promise((resolve, reject) => {
            api.editForUser(
                payload.user_id,
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
    getSettingConfig({ commit }) {
        return new Promise((resolve, reject) => {
            api.getSettingConfig(
                settings => {
                    commit("setAllSettings", settings)
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    }
}

// mutations
const mutations = {
    setUserSettings(state, userSettings) {
        state.all = userSettings
    },
    setAllSettings(state, settings) {
        state.all_settings = settings.all_settings
        state.all_settings_name = settings.all_setting_names
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
