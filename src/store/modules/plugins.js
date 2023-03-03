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
}

// actions
const actions = {
    getPlugins({ commit }, {use_cache}) {
        return new Promise((resolve, reject) => {
            if (getters.pluginCount == 0 || (use_cache !== undefined && use_cache == false)) {
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
            commit('setFetchingServersInProgress', true)
            api.getIndexValues(indexValues => {
                commit("setPluginIndexValues", indexValues)
                resolve()
            },
                (error) => { reject(error) }
            )
            commit('setFetchingServersInProgress', false)
        })
    },
}

// mutations
const mutations = {
    setPlugins(state, plugins) {
        state.all = plugins
    },

    setFetchingServersInProgress(state, flag) {
        state.fetching_index_in_progress = flag
    },

    setPluginIndexValues(state, indexValues) {
        for (const [serverID, indexValue] of Object.entries(indexValues)) {
            if (state.pluginIndexValues[serverID] === undefined) {
                Vue.set(state.pluginIndexValues, serverID, {})
            }
            state.pluginIndexValues[serverID] = Object.assign({}, state.pluginIndexValues[serverID], indexValue)
        }
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
