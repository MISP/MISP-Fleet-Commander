import Vue from "vue"
import api from "@/api/health"

export const SEVERITIES = ["critical", "warning", "info"]
export const CATEGORIES = ["availability", "version", "workers", "sync", "services", "config", "freshness", "users"]

const PENDING_TIMEOUT_MS = 90 * 1000
// Live updates carry issues, not the summary (server list, refresh times): reload it once updates settle
const SUMMARY_RELOAD_DELAY_MS = 5 * 1000
let summaryReloadTimer = null

export function severityRank(severity) {
    const rank = SEVERITIES.indexOf(severity)
    return rank === -1 ? SEVERITIES.length : rank
}

export function worstSeverity(issues) {
    let worst = null
    issues.forEach((issue) => {
        if (worst === null || severityRank(issue.severity) < severityRank(worst)) {
            worst = issue.severity
        }
    })
    return worst
}

// Most severe first, then the oldest
export function compareIssues(a, b) {
    return severityRank(a.severity) - severityRank(b.severity)
        || (a.first_seen || 0) - (b.first_seen || 0)
        || a.id.localeCompare(b.id)
}

export function emptyCounts() {
    return { critical: 0, warning: 0, info: 0 }
}

// Issues of every fleet of the user, unlike the `servers` module that only tracks the selected fleet.
// Kept up to date by the HEALTH_UPDATED socket event, which carries all current issues of one server.
const state = {
    issuesByServer: {},
    summary: null,
    loaded: false,
    loading: false,
    error: null,
    pending: {},  // server_id -> "test_connection" | "refresh", until the server's next health update
}

const getters = {
    allIssues: (state) => {
        return [].concat(...Object.values(state.issuesByServer))
    },
    activeIssues: (state, getters) => {
        return getters.allIssues.filter(issue => issue.ack === null)
    },
    acknowledgedIssues: (state, getters) => {
        return getters.allIssues.filter(issue => issue.ack !== null)
    },
    counts: (state, getters) => {
        const counts = emptyCounts()
        getters.activeIssues.forEach((issue) => { counts[issue.severity] += 1 })
        return counts
    },
    // What the navigation shows: info issues do not need attention
    attentionCount: (state, getters) => {
        return getters.counts.critical + getters.counts.warning
    },
    fleetCounts: (state, getters) => {
        const counts = {}
        getters.activeIssues.forEach((issue) => {
            if (counts[issue.fleet_id] === undefined) {
                counts[issue.fleet_id] = emptyCounts()
            }
            counts[issue.fleet_id][issue.severity] += 1
        })
        return counts
    },
    // server_id -> unacknowledged issues, most severe first
    serverActiveIssues: (state) => {
        const byServer = {}
        Object.entries(state.issuesByServer).forEach(([server_id, issues]) => {
            byServer[server_id] = issues.filter(issue => issue.ack === null).sort(compareIssues)
        })
        return byServer
    },
    topIssues: (state, getters) => (limit) => {
        return getters.activeIssues.slice().sort(compareIssues).slice(0, limit)
    },
    serverWorst: (state) => {
        const worst = {}
        Object.entries(state.issuesByServer).forEach(([server_id, issues]) => {
            worst[server_id] = worstSeverity(issues.filter(issue => issue.ack === null))
        })
        return worst
    },
}

const actions = {
    init({ state, dispatch }) {
        if (state.loaded || state.loading) {
            return Promise.resolve()
        }
        return dispatch("fetch")
    },
    fetch({ commit }) {
        commit("setLoading", true)
        const issues = new Promise((resolve, reject) => {
            api.issues({ include_acked: 1 }, resolve, reject)
        })
        const summary = new Promise((resolve, reject) => {
            api.summary(resolve, reject)
        })
        return Promise.all([issues, summary])
            .then(([issueList, summaryData]) => {
                commit("setAllIssues", issueList)
                commit("setSummary", summaryData)
                commit("setError", null)
            })
            .catch((error) => {
                commit("setError", error)
            })
            .finally(() => {
                commit("setLoading", false)
            })
    },
    acknowledge({ commit }, payload) {
        return new Promise((resolve, reject) => {
            api.acknowledge(
                payload,
                (issue) => {
                    commit("updateIssue", issue)
                    resolve(issue)
                },
                reject,
            )
        })
    },
    unacknowledge({ commit }, issue) {
        return new Promise((resolve, reject) => {
            api.unacknowledge(
                issue.id,
                () => {
                    commit("updateIssue", Object.assign({}, issue, { ack: null }))
                    resolve()
                },
                reject,
            )
        })
    },
    markPending({ commit, state }, { server_id, kind }) {
        commit("setPending", { server_id, kind })
        setTimeout(() => {
            if (state.pending[server_id] === kind) {
                commit("setPending", { server_id, kind: null })
            }
        }, PENDING_TIMEOUT_MS)
    },
    reloadSummary({ commit }) {
        clearTimeout(summaryReloadTimer)
        summaryReloadTimer = setTimeout(() => {
            api.summary((summary) => commit("setSummary", summary), () => {})
        }, SUMMARY_RELOAD_DELAY_MS)
    },
    SOCKET_HEALTH_UPDATED({ commit, dispatch, state }, payload) {
        if (!state.loaded || payload === null || typeof payload !== "object") {
            return
        }
        commit("setServerIssues", payload)
        commit("setPending", { server_id: payload.server_id, kind: null })
        dispatch("reloadSummary")
    },
    // Updates may have been missed while disconnected
    SOCKET_CONNECT({ state, dispatch }) {
        if (state.loaded && !state.loading) {
            dispatch("fetch")
        }
    },
}

const mutations = {
    setLoading(state, loading) {
        state.loading = loading
    },
    setError(state, error) {
        state.error = error
    },
    setSummary(state, summary) {
        state.summary = summary
    },
    setAllIssues(state, issues) {
        const byServer = {}
        Object.keys(state.issuesByServer).forEach((server_id) => { byServer[server_id] = [] })
        issues.forEach((issue) => {
            if (byServer[issue.server_id] === undefined) {
                byServer[issue.server_id] = []
            }
            byServer[issue.server_id].push(issue)
        })
        state.issuesByServer = byServer
        state.loaded = true
    },
    setServerIssues(state, { server_id, issues }) {
        Vue.set(state.issuesByServer, server_id, issues)
    },
    updateIssue(state, updated) {
        const issues = state.issuesByServer[updated.server_id]
        if (issues === undefined) {
            return
        }
        const index = issues.findIndex(issue => issue.id === updated.id)
        if (index !== -1) {
            Vue.set(issues, index, Object.assign({}, issues[index], { ack: updated.ack }))
        }
    },
    setPending(state, { server_id, kind }) {
        if (kind === null) {
            Vue.delete(state.pending, server_id)
        } else {
            Vue.set(state.pending, server_id, kind)
        }
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
}
