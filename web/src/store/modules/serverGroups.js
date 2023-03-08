import api from "@/api/serverGroups"
import Vue from "vue"

// initial state
const state = {
    all: {},
    selected: null
}

// getters
const getters = {
    serverGroupCount: state => {
        return Object.values(state.all).length
    },
    selectedServerGroup: state => {
        return state.selected
    }
}

// actions
const actions = {
    initFetch({ commit, getters }, payload) {
        return new Promise((resolve, reject) => {
            if (
                payload === undefined ||
                (!payload.use_cache || getters.serverGroupCount == 0)
            ) {
                api.index(
                    groups => {
                        groups.forEach(group => {
                            group._loading = false
                        })
                        commit("setServerGroups", groups)
                        resolve()
                    },
                    (error) => { reject(error) }
                )
            } else {
                resolve("Server groups already loaded")
            }
        })
    },
    getServerGroups({ commit }) {
        return new Promise((resolve, reject) => {
            api.index(
                groups => {
                    groups.forEach(group => {
                        group._loading = false
                    })
                    commit("setServerGroups", groups)
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    getServerGroup({ commit }, id) {
        return new Promise((resolve, reject) => {
            api.get(
                id,
                group => {
                    commit("setGroup", group)
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    selectServerGroup({ commit, dispatch }, group) {
        return new Promise((resolve, reject) => {
            dispatch("servers/resetState", undefined, {root: true})
            commit("selectServerGroup", group)
        })
    },
    selectServerGroupFromServerId({ commit, dispatch }, server_id) {
        return new Promise((resolve, reject) => {
            dispatch("initFetch", { use_cache: false })
            api.getFromServerId(
                server_id,
                group => {
                    dispatch("selectServerGroup", group)
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    addServerGroup({ commit }, payload={}) {
        return new Promise((resolve, reject) => {
            api.add(
                payload,
                group => {
                    commit("setServerGroup", group)
                    resolve()
                },
                (error) => { reject(error) }
            )
        }) 
    },
    deleteServerGroup({ dispatch }, payload={}) {
        return new Promise((resolve, reject) => {
            api.delete(
                payload,
                (response) => {
                    dispatch("getServerGroups")
                    .then(() => {
                        resolve(response)
                    })
                },
                (error) => { reject(error) }
            )
        }) 
    },
}

// mutations
const mutations = {
    selectServerGroup: function (state, group) {
        state.selected = group
    },
    setServerGroups(state, groups) {
        Vue.set(state, 'all', {})
        groups.forEach(group => {
            Vue.set(state.all, group.id, group)
        })
    },
    setServerGroup(state, group) {
        for (let i = 0; i < state.all.length; i++) {
            if (state.all[i].id == group.vid) {
                const updatedGroup = state.all[i] = {...state.all[i], group}
                Vue.set(state.all, i, updatedGroup)
                break
            }
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
