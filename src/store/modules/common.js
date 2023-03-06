// initial state
const state = {
}

// getters
const getters = {}

// actions
const actions = {
    fetchGithubVersion({ commit }) {
        return new Promise((resolve, reject) => {
            api.fetchGithubVersion(
                (githubReply) => {
                    commit("setGithubVersion", githubReply)
                    resolve()
                },
                (error) => {
                    reject(error)
                }
            )
        })
    },
}

// mutations
const mutations = {
    setGithubVersion(state, githubReply) {
        const githubVersion = githubReply.tag_name
        state.githubVersion = githubVersion
        setUpdatableServers(state)
    }
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
