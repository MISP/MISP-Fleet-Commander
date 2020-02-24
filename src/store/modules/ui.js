// initial state
const state = {
    sidebarCollapsed: true
}

// getters
const getters = {}

// actions
const actions = {}

// mutations
const mutations = {
    toggleSidebar: function (state) {
        state.sidebarCollapsed = !state.sidebarCollapsed
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
