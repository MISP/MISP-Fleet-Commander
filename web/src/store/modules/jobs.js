import Vue from "vue"
import api from "@/api/jobs"
import { isFinalJob, mergeJob } from "@/helpers/jobs"

// Jobs this tab knows about, kept up to date by JOB_STARTED / JOB_PROGRESS / JOB_DONE. Jobs started from this tab
// are "tracked": when one ends, it is queued in `finished` for the notifier to announce
const state = {
    jobs: {},
    tracked: {},
    announced: {},
    finished: [],
}

const getters = {
    job: (state) => (job_id) => {
        return state.jobs[job_id] || null
    },
    unfinishedTrackedJobs: (state) => {
        return Object.keys(state.tracked).map(id => state.jobs[id]).filter(job => job && !isFinalJob(job))
    },
}

function promised(call) {
    return new Promise((resolve, reject) => {
        call(resolve, reject)
    })
}

const actions = {
    create({ commit, dispatch }, payload) {
        return promised((resolve, reject) => {
            api.create(payload, (data) => {
                commit("track", data.job_id)
                commit("setJob", data.job)
                // The job may have progressed, or even ended, before this answer arrived: catch up
                dispatch("fetch", data.job_id).catch(() => {})
                resolve(data.job)
            }, reject)
        })
    },
    fetch({ commit }, job_id) {
        return promised((resolve, reject) => {
            api.get(job_id, (job) => {
                commit("setJob", job)
                resolve(job)
            }, reject)
        })
    },
    cancel(context, job_id) {
        return promised((resolve, reject) => {
            api.cancel(job_id, resolve, reject)
        })
    },
    retry({ commit, dispatch }, { job_id, only_failed }) {
        return promised((resolve, reject) => {
            api.retry(job_id, only_failed, (data) => {
                commit("track", data.job_id)
                commit("setJob", data.job)
                dispatch("fetch", data.job_id).catch(() => {})
                resolve(data.job)
            }, reject)
        })
    },
    // After a reconnection, events may have been missed
    refreshUnfinished({ state, dispatch }) {
        Object.values(state.jobs).filter(job => !isFinalJob(job)).forEach((job) => {
            dispatch("fetch", job.id).catch(() => {})
        })
    },
    SOCKET_JOB_STARTED({ commit, state }, payload) {
        if (state.jobs[payload.job_id]) {
            commit("patchJob", { id: payload.job_id, status: "running", started: payload.started })
        }
    },
    SOCKET_JOB_PROGRESS({ commit, state }, payload) {
        if (state.jobs[payload.job_id]) {
            commit("applyProgress", payload)
        }
    },
    SOCKET_JOB_DONE({ commit, dispatch, state }, payload) {
        if (state.jobs[payload.job_id]) {
            commit("patchJob", {
                id: payload.job_id, status: payload.status, succeeded: payload.succeeded,
                failed: payload.failed, finished: payload.finished,
            })
            // Results whose progress event was missed come with the final state
            dispatch("fetch", payload.job_id).catch(() => {})
        }
    },
    SOCKET_CONNECT({ dispatch }) {
        dispatch("refreshUnfinished")
    },
}

function announceIfFinished(state, job) {
    if (state.tracked[job.id] && isFinalJob(job) && !state.announced[job.id]) {
        Vue.set(state.announced, job.id, true)
        state.finished.push({
            id: job.id, title: job.title, kind: job.kind, status: job.status,
            total: job.total, succeeded: job.succeeded, failed: job.failed,
        })
    }
}

const mutations = {
    track(state, job_id) {
        Vue.set(state.tracked, job_id, true)
    },
    setJob(state, job) {
        const merged = mergeJob(state.jobs[job.id], job)
        Vue.set(state.jobs, job.id, merged)
        announceIfFinished(state, merged)
    },
    patchJob(state, patch) {
        const current = state.jobs[patch.id]
        if (!current) {
            return
        }
        if (isFinalJob(current) && patch.status && !isFinalJob(patch)) {
            return  // A late "started" after the end
        }
        const merged = Object.assign({}, current, patch)
        Vue.set(state.jobs, patch.id, merged)
        announceIfFinished(state, merged)
    },
    applyProgress(state, payload) {
        const current = state.jobs[payload.job_id]
        const results = (current.results || []).map((result) => {
            return result.id === payload.result.id ? payload.result : result
        })
        const merged = Object.assign({}, current, {
            results,
            status: isFinalJob(current) ? current.status : "running",
            succeeded: Math.max(current.succeeded || 0, payload.succeeded || 0),
            failed: Math.max(current.failed || 0, payload.failed || 0),
            done: results.filter(result => result.status !== "pending").length,
        })
        Vue.set(state.jobs, payload.job_id, merged)
    },
    takeFinished(state) {
        state.finished.splice(0, state.finished.length)
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
}
