import api from "@/api/plugins"
import Vue from "vue"

// initial state
const state = {
    all: [],
    fetching_index_in_progress: false,
    fetching_view_in_progress: false,
    fetching_notifications_in_progress: false,
    pluginIndexValues: {},
    pluginViewValues: {},
    pluginNotifications: {},
}

// getters
const getters = {
    pluginCount: state => {
        return state.all.length
    },
    allPlugins: state => {
        return state.all
    },
    enabledPlugins: (state, getter, rootState, rootGetter) => {
        const userSettingsByName = rootGetter['userSettings/getLoggedUserSettingsByName']
        let enabledPluginIDs = []
        if (userSettingsByName && userSettingsByName['Plugins.enabled_plugins']) {
            enabledPluginIDs = userSettingsByName['Plugins.enabled_plugins']
        }
        return getter.allPlugins.filter(plugin => {
            return enabledPluginIDs.includes(plugin.id)
        })
    },
    indexPlugins: (state, getter) => {
        return getter.enabledPlugins.filter(plugin => plugin.features.index)
    },
    viewPlugins: (state, getter) => {
        return getter.enabledPlugins.filter(plugin => plugin.features.view)
    },
    actionPlugins: (state, getter) => {
        return getter.enabledPlugins.filter(plugin => plugin.features.action)
    },
    notificationPlugins: (state, getter) => {
        return getter.enabledPlugins.filter(plugin => plugin.features.notifications)
    },
    pluginNotificationFor: (state, getter) => (server_id, plugin_id) => {
        return state.pluginNotifications[server_id] ? (state.pluginNotifications[server_id][plugin_id] ? state.pluginNotifications[server_id][plugin_id] : []) : []
    }
}

// actions
const actions = {
    getPlugins({ commit }, {use_cache}) {
        return new Promise((resolve, reject) => {
            if (state.all.length == 0 || (use_cache !== undefined && use_cache == false)) {
                api.index(
                    plugins => {
                        commit("setPlugins", plugins)
                        resolve()
                    },
                    (error) => { reject(error) }
                )
            } else {
                resolve('Plugins already loaded')
            }
        })
    },
    fetchIndexValues({ commit }, { no_cache }) {
        return new Promise((resolve, reject) => {
            commit('setFetchingServersIndexInProgress', true)
            api.getIndexValues(indexValues => {
                commit("setPluginIndexValues", indexValues)
                commit('setFetchingServersIndexInProgress', false)
                resolve()
            },
                (error) => { 
                    commit('setFetchingServersIndexInProgress', false)
                    reject(error)
                }
            )
        })
    },
    fetchViewValues({ commit }, { no_cache, serverID }) {
        return new Promise((resolve, reject) => {
            commit('setFetchingServerViewInProgress', true)
            api.getViewValues(serverID, viewValues => {
                commit("setPluginViewValues", { serverID: serverID, viewValues: viewValues})
                commit('setFetchingServerViewInProgress', false)
                resolve()
            },
                (error) => { 
                    reject(error)
                    commit('setFetchingServerViewInProgress', false)
                }
            )
        })
    },
    fetchNotifications({ commit }, { no_cache, serverID }) {
        return new Promise((resolve, reject) => {
            commit('setFetchingServerNotificationInProgress', true)
            api.getNotifications(serverID, notifications => {
                commit("setPluginNotifications", { serverID: serverID, notifications: notifications })
                commit('setFetchingServerNotificationInProgress', false)
                resolve()
            },
                (error) => { 
                    reject(error)
                    commit('setFetchingServerNotificationInProgress', false)
                }
            )
        })
    },
}

// mutations
const mutations = {
    setPlugins(state, plugins) {
        state.all = plugins
    },

    setFetchingServersIndexInProgress(state, flag) {
        state.fetching_index_in_progress = flag
    },
    setFetchingServerViewInProgress(state, flag) {
        state.fetching_view_in_progress = flag
    },
    setFetchingServerNotificationInProgress(state, flag) {
        state.fetching_notifications_in_progress = flag
    },

    setPluginIndexValues(state, indexValues) {
        for (const [serverID, indexValue] of Object.entries(indexValues)) {
            if (state.pluginIndexValues[serverID] === undefined) {
                Vue.set(state.pluginIndexValues, serverID, {})
            }
            state.pluginIndexValues[serverID] = Object.assign({}, state.pluginIndexValues[serverID], indexValue)
        }
    },

    setPluginViewValues(state, {serverID, viewValues}) {
        if (state.pluginViewValues[serverID] === undefined) {
            Vue.set(state.pluginViewValues, serverID, {})
        }
        state.pluginViewValues[serverID] = Object.assign({}, state.pluginViewValues[serverID], viewValues)
    },

    setPluginNotifications(state, { serverID, notifications }) {
        if (state.pluginNotifications[serverID] === undefined) {
            Vue.set(state.pluginNotifications, serverID, {})
        }
        state.pluginNotifications[serverID] = Object.assign({}, state.pluginNotifications[serverID], notifications)
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
