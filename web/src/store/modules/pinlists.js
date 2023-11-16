import api from "@/api/pinLists"

// initial state
const state = {
    all: [],
    pinListItems: [],
    entriesFromPinned: [],
}

// getters
const getters = {
    pinnedEvents: state => {
        return state.all.filter(entry => entry.model == 'event')
    },
    pinnedSharingGroups: state => {
        return state.all.filter(entry => entry.model == 'sharinggroup')
    },
    pinnedSightings: state => {
        return state.all.filter(entry => entry.model == 'sighting')
    },
    pinnedByID: state => {
        const pinnedByID = {}
        state.all.forEach(entry => {
            pinnedByID[entry.id] = entry
        });
        return pinnedByID
    },
    entriesByPinnedID: state => {
        const entryByPinned = {}
        state.entriesFromPinned.forEach(entry => {
            if (!entryByPinned[entry.pinlist_id]) {
                entryByPinned[entry.pinlist_id] = []
            }
            entryByPinned[entry.pinlist_id].push(entry)
        })
        return entryByPinned
    },
    entriesByServerID: state => {
        const entryByServer = {}
        state.entriesFromPinned.forEach(entry => {
            if (!entryByServer[entry.server_id]) {
                entryByServer[entry.server_id] = []
            }
            entryByServer[entry.server_id].push(entry)
        })
        return entryByServer
    },
}

// actions
const actions = {
    fetchIndex({ commit }) {
        return new Promise((resolve, reject) => {
            api.index(
                (pinLists) => {
                    commit("setPinlists", pinLists)
                    resolve(pinLists)
                },
                (error) => { reject(error) }
            )
        })
    },

    add({ dispatch }, payload) {
        return new Promise((resolve, reject) => {
            api.add(
                payload,
                (response) => {
                    dispatch("fetchIndex")
                    if (response.error !== undefined) {
                        reject(response.error)
                    } else {
                        resolve(response)
                    }
                },
                (error) => { reject(error) }
            )
        })
    },

    delete({ dispatch }, entry_id) {
        return new Promise((resolve, reject) => {
            api.delete(
                entry_id,
                (response) => {
                    dispatch("fetchIndex")
                    resolve(response)
                },
                (error) => { reject(error) }
            )
        })
    },

    deleteFromServer({ dispatch }, payload) {
        return new Promise((resolve, reject) => {
            api.deleteFromServer(
                payload.entry_id,
                payload.server_id,
                (response) => {
                    resolve(response)
                    dispatch("refreshServerEntry", payload)
                },
                (error) => {
                    reject(error)
                    dispatch("refreshServerEntry", payload)
                }
            )
        })
    },

    deleteFromServers({ }, entry_id) {
        return new Promise((resolve, reject) => {
            api.deleteFromServers(
                entry_id,
                (response) => {
                    resolve(response)
                    dispatch("refreshAllServers", entry_id)
                },
                (error) => {
                    reject(error)
                    dispatch("refreshAllServers", entry_id)
                }
            )
        })
    },

    refreshServerEntry({ dispatch }, payload) {
        return new Promise((resolve, reject) => {
            api.refreshServerEntry(
                payload.entry_id,
                payload.server_id,
                (result) => {
                    resolve(result)
                    dispatch("getAllFromServer", payload.server_id)
                },
                (error) => { reject(error) }
            )
        })
    },

    refreshAllServers({ }, entry_id) {
        return new Promise((resolve, reject) => {
            api.refreshAllServers(
                entry_id,
                (result) => {
                    resolve(result)
                },
                (error) => { reject(error) }
            )
        })
    },

    getAllEntries({ commit }) {
        return new Promise((resolve, reject) => {
            api.getAllEntries(
                (entries) => {
                    commit("setEntries", entries)
                    resolve(entries)
                },
                (error) => { reject(error) }
            )
        })
    },

    getAllFromServer({ commit }, server_id) {
        return new Promise((resolve, reject) => {
            api.getAllFromServer(
                server_id,
                (entries) => {
                    commit("setEntriesForServer", { server_id: server_id, entries: entries })
                    resolve(entries)
                },
                (error) => { reject(error) }
            )
        })
    },

    getEntriesFromPinned({ commit }, entry_id) {
        return new Promise((resolve, reject) => {
            api.getEntriesFromPinned(
                entry_id,
                (entriesFromPinned) => {
                    const payload = {pinlist_id: entry_id, entries: entriesFromPinned}
                    commit("setEntriesFromPinned", payload)
                    resolve(entriesFromPinned)
                },
                (error) => { reject(error) }
            )
        })
    },

    publishEventOnServer({ }, payload) {
        return new Promise((resolve, reject) => {
            api.publishEventOnServer(
                payload.entry_id,
                payload.server_id,
                (result) => {
                    resolve(result)
                },
                (error) => { reject(error) }
            )
        })
    },
}

// mutations
const mutations = {
    setPinlists(state, pinLists) {
        state.all = pinLists
    },
    setEntriesFromPinned(state, payload) {
        const pinlist_id = payload.pinlist_id
        const entries = payload.entries
        state.entriesFromPinned = state.entriesFromPinned.filter(entry => entry.pinlist_id != pinlist_id)
        entries.forEach(entry => {
            state.entriesFromPinned.push(entry)
        });
    },
    setEntries(state, entries) {
        state.entriesFromPinned = entries
    },
    setEntriesForServer(state, payload) {
        const server_id = payload.server_id
        const entries = payload.entries
        state.entriesFromPinned = state.entriesFromPinned.filter(entry => entry.server_id != server_id)
        entries.forEach(entry => {
            state.entriesFromPinned.push(entry)
        });
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
