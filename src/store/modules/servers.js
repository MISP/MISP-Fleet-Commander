import api from "@/api/servers"

// initial state
const state = {
    all: []
}

// getters
const getters = {
    serverCount: state => {
        return state.all.length
    }
}

// actions
const actions = {
    getAllServers ({ commit }) {
        // this function should not fetch data if it has been fetched already
        return new Promise((resolve, reject) => {
            api.index(
                servers => {
                    commit("setServers", servers)
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    }
}

// mutations
const mutations = {
    setServers (state, servers) {
        state.all = servers
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}