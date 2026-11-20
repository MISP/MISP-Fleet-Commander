import Vue from "vue"
import api from "@/api/health"

export const SEVERITIES = ["critical", "warning", "info"]
export const CATEGORIES = ["availability", "version", "workers", "sync", "services", "config", "freshness", "users", "queries"]

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

// Most severe first, then the oldest. IDs compare as plain strings, as the backend sorts them
export function compareIssues(a, b) {
    return severityRank(a.severity) - severityRank(b.severity)
        || (a.first_seen || 0) - (b.first_seen || 0)
        || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)
}

export function emptyCounts() {
    return { critical: 0, warning: 0, info: 0 }
}

function addCounts(total, counts) {
    SEVERITIES.forEach((severity) => { total[severity] += counts[severity] })
    return total
}

// Issues are frozen: a large fleet can have thousands (a baseline drifting on every server) and making each one
// reactive, then tracking every read of it, is what made the UI slow. They are replaced, never changed in place
function frozenIssues(issues) {
    return Object.freeze((Array.isArray(issues) ? issues : []).map(issue => Object.freeze(issue)))
}

// What the UI shows about one server, computed once per update of that server rather than from every issue of
// every server on each read:
//   - active: unacknowledged issues, most severe first;
//   - counts: unacknowledged issues per severity, and per fleet in `fleetCounts` (from the issues' fleet);
//   - worst: worst unacknowledged severity, or null;
//   - ackedCount: acknowledged issues;
//   - weight: sort key, criticals then warnings then info, by count.
export function serverDigest(issues) {
    const active = issues.filter(issue => issue.ack === null).sort(compareIssues)
    const counts = emptyCounts()
    const fleetCounts = {}
    active.forEach((issue) => {
        if (counts[issue.severity] === undefined) {
            return
        }
        counts[issue.severity] += 1
        if (fleetCounts[issue.fleet_id] === undefined) {
            fleetCounts[issue.fleet_id] = emptyCounts()
        }
        fleetCounts[issue.fleet_id][issue.severity] += 1
    })
    return Object.freeze({
        active: Object.freeze(active),
        counts: Object.freeze(counts),
        fleetCounts: Object.freeze(fleetCounts),
        worst: active.length > 0 ? active[0].severity : null,
        ackedCount: issues.length - active.length,
        weight: counts.critical * 1000000 + counts.warning * 1000 + counts.info,
    })
}

export const EMPTY_DIGEST = serverDigest([])

// Issues of every fleet of the user, unlike the `servers` module that only tracks the selected fleet.
// Kept up to date by the HEALTH_UPDATED socket event, which carries all current issues of one server.
// Components showing one server read `digests[server_id]` from the state: only that server's updates reach them.
const state = {
    issuesByServer: {},  // server_id -> frozen issues, acknowledged ones included
    digests: {},  // server_id -> serverDigest of its issues
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
    activeIssues: (state) => {
        return [].concat(...Object.values(state.digests).map(digest => digest.active))
    },
    acknowledgedIssues: (state, getters) => {
        return getters.allIssues.filter(issue => issue.ack !== null)
    },
    counts: (state) => {
        return Object.values(state.digests).reduce((total, digest) => addCounts(total, digest.counts), emptyCounts())
    },
    // What the navigation shows: info issues do not need attention
    attentionCount: (state, getters) => {
        return getters.counts.critical + getters.counts.warning
    },
    fleetCounts: (state) => {
        const counts = {}
        Object.values(state.digests).forEach((digest) => {
            Object.entries(digest.fleetCounts).forEach(([fleet_id, fleetCounts]) => {
                counts[fleet_id] = addCounts(counts[fleet_id] || emptyCounts(), fleetCounts)
            })
        })
        return counts
    },
    // server_id -> unacknowledged issues, most severe first
    serverActiveIssues: (state) => {
        const byServer = {}
        Object.entries(state.digests).forEach(([server_id, digest]) => {
            byServer[server_id] = digest.active
        })
        return byServer
    },
    // The most severe issues of all servers: each server's list is sorted, so its first `limit` are enough
    topIssues: (state) => (limit) => {
        const candidates = [].concat(...Object.values(state.digests).map(digest => digest.active.slice(0, limit)))
        return candidates.sort(compareIssues).slice(0, limit)
    },
    serverWorst: (state) => {
        const worst = {}
        Object.entries(state.digests).forEach(([server_id, digest]) => {
            worst[server_id] = digest.worst
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
    // payload: { issue_ids, until?, note? }. Resolves with { acknowledged, skipped }
    acknowledgeMany({ commit }, payload) {
        return new Promise((resolve, reject) => {
            api.acknowledgeMany(
                payload,
                (result) => {
                    commit("updateIssues", result.acknowledged)
                    resolve(result)
                },
                reject,
            )
        })
    },
    // Resolves with { unacknowledged, skipped }
    unacknowledgeMany({ commit }, issues) {
        return new Promise((resolve, reject) => {
            api.unacknowledgeMany(
                issues.map(issue => issue.id),
                (result) => {
                    const shown = new Set(result.unacknowledged)
                    commit("updateIssues", issues
                        .filter(issue => shown.has(issue.id))
                        .map(issue => ({ id: issue.id, server_id: issue.server_id, ack: null })))
                    resolve(result)
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
        const lists = {}
        Object.keys(state.issuesByServer).forEach((server_id) => { lists[server_id] = [] })
        issues.forEach((issue) => {
            if (lists[issue.server_id] === undefined) {
                lists[issue.server_id] = []
            }
            lists[issue.server_id].push(issue)
        })
        const byServer = {}
        const digests = {}
        Object.entries(lists).forEach(([server_id, list]) => {
            byServer[server_id] = frozenIssues(list)
            digests[server_id] = serverDigest(byServer[server_id])
        })
        state.issuesByServer = byServer
        state.digests = digests
        state.loaded = true
    },
    setServerIssues(state, { server_id, issues }) {
        const frozen = frozenIssues(issues)
        Vue.set(state.issuesByServer, server_id, frozen)
        Vue.set(state.digests, server_id, serverDigest(frozen))
    },
    updateIssue(state, updated) {
        mutations.updateIssues(state, [updated])
    },
    // Applies the `ack` of each updated issue to the issue it knows: each server's list is replaced once, however many
    // of its issues change (a bulk acknowledgement can change thousands)
    updateIssues(state, updates) {
        const byServer = new Map()  // server_id -> Map(issue ID -> ack)
        updates.forEach((updated) => {
            if (!byServer.has(updated.server_id)) {
                byServer.set(updated.server_id, new Map())
            }
            byServer.get(updated.server_id).set(updated.id, updated.ack)
        })
        byServer.forEach((acks, server_id) => {
            const issues = state.issuesByServer[server_id]
            if (issues === undefined || !issues.some(issue => acks.has(issue.id))) {
                return
            }
            const replaced = issues.map(issue => (acks.has(issue.id) ? Object.assign({}, issue, { ack: acks.get(issue.id) }) : issue))
            mutations.setServerIssues(state, { server_id, issues: replaced })
        })
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
