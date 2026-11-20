import common from "./common"

// Fleet queries: one MispQL statement run on many servers, as a job. Every call returns a promise of the answer's
// data; a failure rejects with a message

function data(response) {
    return response.data
}

function message(error) {
    return new Promise((resolve, reject) => {
        common.handleError(error, reject)
    })
}

function get(url, params) {
    return common.getClient().get(url, { params }).then(data).catch(message)
}

function idList(ids) {
    return Array.isArray(ids) ? ids.join(",") : undefined
}

export default {
    // Keywords, tables (default columns, aliases, sort names), FORMATs and the LIMIT cap
    language() {
        return get("/queries/language")
    },
    // What a statement is, or its mistakes on the text; nothing is sent to any server
    check(statement) {
        return common.getClient().post("/queries/check", { statement }).then(data).catch(message)
    },
    // Resolves `{ ok: true, job_id, job, notes }`, or `{ ok: false, message, errors }` when the statement cannot run
    // (its mistakes placed on the text: the client's usual error handling would keep only the message)
    run({ statement, server_ids, title }) {
        return common.getClient().post("/queries", { statement, server_ids, title }, {
            validateStatus: status => (status >= 200 && status < 300) || status === 400,
        }).then((response) => {
            if (response.status === 400) {
                return Object.assign({ ok: false, errors: [] }, response.data)
            }
            return Object.assign({ ok: true }, response.data)
        }).catch(message)
    },
    // A run: the job, its statement, each server's summary and whether its rows are kept
    get(job_id) {
        return get(`/queries/${encodeURIComponent(job_id)}`)
    },
    rows(job_id, { offset = 0, limit = 100, server_id } = {}) {
        return get(`/queries/${encodeURIComponent(job_id)}/rows`, { offset, limit, server_id })
    },
    capabilities({ server_ids, refresh = false }) {
        return get("/queries/capabilities", { server_ids: idList(server_ids), refresh: refresh ? 1 : undefined })
    },
    describe({ table, server_ids, refresh = false }) {
        return get("/queries/describe", { table, server_ids: idList(server_ids), refresh: refresh ? 1 : undefined })
    },
    // The user's latest runs
    recent(limit = 10) {
        return get("/jobs", { kind: "mispql_query", limit })
    },
    fleets() {
        return get("/fleets/index")
    },
    serversOfFleet(fleet_id) {
        return get(`/servers/index/${encodeURIComponent(fleet_id)}`)
    },
}
