import api from "@/api/userSettings"

// initial state
const state = {
    logged_user_settings: [],
    all_user_settings: {},
    all_settings: {},
    all_settings_name: {},
}

// getters
const getters = {
    getLoggedUserSetting: state => {
        return state.logged_user_settings
    },
    getLoggedUserSettingsByName: (state, getter) => {
        const settingByName = {}
        getter.getLoggedUserSetting.forEach(setting => {
            settingByName[setting.name] = setting.value
        });
        return settingByName
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
    },
    togglePlugin({ commit }, pluginName) {
        return new Promise((resolve, reject) => {
            api.togglePlugin(
                pluginName,
                enabled_plugins => {
                    // commit("setAllSettings", settings)
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
        state.logged_user_settings = userSettings
    },
    setAllUserSettings(state, allUserSettings) {
        state.all_user_settings = allUserSettings
    },
    setAllSettings(state, settings) {
        state.all_settings = settings.all_settings
        state.all_settings_name = settings.all_setting_names
    },
    setEnabledPlugin(state, enabled_plugins) {
        
    }
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
