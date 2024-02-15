import api from "@/api/users"

// initial state
const state = {
    all: []
}

// getters
const getters = {
    userCount: state => {
        return state.all.length
    },
    getUserList: state => {
        return state.all
    },
}

// actions
const actions = {
    getUsers({ commit }, payload={}) {
        return new Promise((resolve, reject) => {
            api.index(
                users => {
                    commit("setUsers", users)
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    add({ commit }, payload) {
        return new Promise((resolve, reject) => {
            api.add(
                payload,
                () => {
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    edit({ commit }, payload) {
        return new Promise((resolve, reject) => {
            api.edit(
                payload,
                () => {
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    delete({ commit }, user_id) {
        return new Promise((resolve, reject) => {
            api.delete(
                user_id,
                () => {
                    resolve()
                },
                (error) => { reject(error) }
            )
        })
    },
    genAPIKey({ }, user_id) {
        return new Promise((resolve, reject) => {
            api.genAPIKey(
                user_id,
                (data) => {
                    resolve(data)
                },
                (error) => { reject(error) }
            )
        })
    },
}

// mutations
const mutations = {
    setUsers(state, users) {
        state.all = users
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
