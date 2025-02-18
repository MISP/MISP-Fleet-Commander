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
                    resolve(fleet)
                },
                (error) => { reject(error) }
            )
        })
    },
    selectFleet({ commit, dispatch }, payload) {
        return new Promise((resolve, reject) => {
            const fleet_id = payload.data.id
            const redirect = payload.redirect !== undefined ? payload.redirect : true
            dispatch("getFleet", fleet_id).then((fleet) => {
                dispatch("servers/resetState", undefined, {root: true})
                commit("selectFleet", { data: fleet, redirect: redirect })
                resolve()
            })
        })
    },
    selectFleetFromServerId({ commit, dispatch }, server_id) {
        return new Promise((resolve, reject) => {
            dispatch("initFetch", { use_cache: false })
            api.getFromServerId(
                server_id,
                fleet => {
                    dispatch("selectFleet", { data: fleet, redirect: false}).then(() => {
                        resolve()
                    })
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
        if (redirect && router.history.current.name !== 'fleet.view') {
            router.push({ name: 'fleet.view', params: { fleet_id: fleet.id }, replace: true })
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
            if (state.all[i].id == fleet.id) {
                const updatedFleet = state.all[i] = {...state.all[i], fleet}
                Vue.set(state.all, i, updatedFleet)
                break
            }
        }
    },
    setFleetTimestamps(state, fleetTimestamps) {
        const knownFleets = Object.values(state.all) // Looks like we cannot use getters in mutation
        for (let i = 0; i < knownFleets.length; i++) {
            if (knownFleets[i].id == fleetTimestamps.fleet_id) {
                if (fleetTimestamps.watched_timestamp) {
                    knownFleets[i].watched_timestamp = fleetTimestamps.watched_timestamp
                    if (state.selected !== null) {
                        if (state.selected.id == fleetTimestamps.fleet_id)
                            state.selected.watched_timestamp = fleetTimestamps.watched_timestamp
                    }
                }
                if (fleetTimestamps.monitored_timestamp) {
                    if (state.selected !== null) {
                        if (state.selected.id == fleetTimestamps.fleet_id)
                            state.selected.monitored_timestamp = fleetTimestamps.monitored_timestamp
                    }
                }
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
