// initial state
const state = {
    sidebarCollapsed: true,
    worker_health_status: null,
}

// getters
const getters = {}

// actions
const actions = {
    setWorkerHealthStatus({ commit }, healthStatus) {
        return commit("setWorkerHealthStatus", healthStatus)
    },
}

// mutations
const mutations = {
    toggleSidebar: function (state) {
        state.sidebarCollapsed = !state.sidebarCollapsed
    },
    setWorkerHealthStatus: function (state, healthStatus) {
        state.worker_health_status = healthStatus
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
