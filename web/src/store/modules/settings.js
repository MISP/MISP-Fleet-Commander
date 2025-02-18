import api from "@/api/settings"
import Vue from "vue"

// initial state
const state = {
    settings: {
    }
}

// getters
const getters = {
    getSettings: state => {
        return state.settings
    },
    settingsByPanelAndScope: state => {
        const settingsByPanelAndScope = {}
        Object.entries(state.settings).forEach(([setting_id, setting]) => {
            if (settingsByPanelAndScope[setting.panel] === undefined) {
                settingsByPanelAndScope[setting.panel] = {}
            }
            if (settingsByPanelAndScope[setting.panel][setting.scope] === undefined) {
                settingsByPanelAndScope[setting.panel][setting.scope] = {}
            }
            settingsByPanelAndScope[setting.panel][setting.scope][setting_id] = setting
        })
        return settingsByPanelAndScope
    },
    settingValues() {
        const settingValues = {}
        Object.entries(state.settings).forEach(([setting_id, setting]) => {
            settingValues[setting_id] = setting.value
        })
        return settingValues
    },
    isMonitoringEnabled: (state, getters) => {
        return getters.settingValues.monitoring_enabled || false
    },
    isFleetWatchingEnabled: (state, getters) => {
        return getters.settingValues.fleet_watching_enabled || false
    },
}

// actions
const actions = {
    refreshSettings({ commit },) {
            return new Promise((resolve, reject) => {
                api.index(
                    settings => {
                        commit("setSettings", settings)
                        resolve(settings)
                    },
                    (error) => { reject(error) }
                )
            })
        },
    saveSetting({ commit }, payload = {}) {
            return new Promise((resolve, reject) => {
                api.edit(
                    payload,
                    settings => {
                        resolve()
                    },
                    (error) => { reject(error) }
                )
            })
        },
}

// mutations
const mutations = {
    setSettings(state, settings) {
        state.settings = settings
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
}
