import api from "@/api/fleets"
import Vue from "vue"
import router from "@/router"

// initial state
const state = {
    all: {},
    selected: null
}

// getters
const getters = {
    fleetCount: state => {
        return Object.values(state.all).length
    },
    selectedFleet: state => {
        return state.selected
    },
    fleetList: state => {
        return Object.values(state.all)
    }
}

// actions
const actions = {
    initFetch({ commit, getters }, payload) {
        return new Promise((resolve, reject) => {
            if (
                payload === undefined ||
                (!payload.use_cache || getters.fleetCount == 0)
            ) {
                api.index(
                    fleets => {
                        fleets.forEach(fleet => {
                            fleet._loading = false
                        })
                        commit("setFleets", fleets)
                        resolve()
                    },
                    (error) => { reject(error) }
                )
            } else {
                resolve("Fleets already loaded")
            }
        })
    },
    getFleets({ commit }) {
        return new Promise((resolve, reject) => {
            api.index(
                fleets => {
                    fleets.forEach(fleet => {
                        fleet._loading = false
                    })
                    commit("setFleets", fleets)
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    getFleet({ commit }, id) {
        return new Promise((resolve, reject) => {
            api.get(
                id,
                fleet => {
                    commit("setFleet", fleet)
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    selectFleet({ commit, dispatch }, payload) {
        return new Promise((resolve, reject) => {
            dispatch("servers/resetState", undefined, {root: true})
            commit("selectFleet", payload)
        })
    },
    selectFleetFromServerId({ commit, dispatch }, server_id) {
        return new Promise((resolve, reject) => {
            dispatch("initFetch", { use_cache: false })
            api.getFromServerId(
                server_id,
                fleet => {
                    dispatch("selectFleet", { data: fleet, redirect: false})
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    addFleet({ commit }, payload={}) {
        return new Promise((resolve, reject) => {
            api.add(
                payload,
                fleet => {
                    commit("setFleet", fleet)
                    resolve()
                },
                (error) => { reject(error) }
            )
        }) 
    },
    editFleet({ commit }, payload={}) {
        return new Promise((resolve, reject) => {
            api.edit(
                payload,
                fleet => {
                    commit("setFleet", fleet)
                    resolve()
                },
                (error) => { reject(error) }
            )
        }) 
    },
    deleteFleet({ }, payload={}) {
        return new Promise((resolve, reject) => {
            api.delete(
                payload,
                (response) => {
                    resolve(response)
                },
                (error) => { reject(error) }
            )
        }) 
    },
}

// mutations
const mutations = {
    selectFleet: function (state, payload) {
        const fleet = payload.data
        const redirect = payload.redirect !== undefined ? payload.redirect : true
        state.selected = fleet
        if (redirect && router.history.current.path !== '/servers') {
            router.push({ path: '/servers', replace: true })
        }
    },
    setFleets(state, fleets) {
        Vue.set(state, 'all', {})
        fleets.forEach(fleet => {
            Vue.set(state.all, fleet.id, fleet)
        })
    },
    setFleet(state, fleet) {
        for (let i = 0; i < state.all.length; i++) {
            if (state.all[i].id == fleet.vid) {
                const updatedFleet = state.all[i] = {...state.all[i], fleet}
                Vue.set(state.all, i, updatedFleet)
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
