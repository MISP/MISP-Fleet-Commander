import api from "@/api/plugins"
import Vue from "vue"

// initial state
const state = {
    all: [],
    fetching_index_in_progress: false,
    fetching_view_in_progress: false,
    pluginIndexValues: {},
    pluginViewValues: {},
}

// getters
const getters = {
    pluginCount: state => {
        return state.all.length
    },
    indexPlugins: state => {
        return state.all.filter(plugin => plugin.features.index)
    },
    viewPlugins: state => {
        return state.all.filter(plugin => plugin.features.view)
    },
    actionPlugins: state => {
        return state.all.filter(plugin => plugin.features.action)
    },
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
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
