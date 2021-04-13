import api from "@/api/serverGroups"
import Vue from "vue"

// initial state
const state = {
    init_done: false,
    all: [],
    selected: null
}

// getters
const getters = {
    serverGroupCount: state => {
        return state.all.length
    },
    selectedServerGroup: state => {
        return state.selected
    }
}

// actions
const actions = {
    initFetch({ commit, state }) {
        return new Promise((resolve, reject) => {
            if (state.init_done) {
                resolve("Init already done")
            } else {
                api.index(
                    groups => {
                        groups.forEach(group => {
                            group._loading = false
                        })
                        commit("setServerGroups", groups)
                        commit("setInitDone")
                        resolve()
                    },
                    (error) => { reject(error) }
                )
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
        commit("selectServerGroup", group)
        dispatch("servers/getAllServers", {init_only: false}, { root: true })
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
    }
}

// mutations
const mutations = {
    selectServerGroup: function (state, group) {
        state.selected = group
    },
    setInitDone(state) {
        state.init_done = true
    },
    setServerGroups(state, groups) {
        state.all = groups
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
