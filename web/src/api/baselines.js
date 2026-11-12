import common from "./common"

// Answers the client handles itself, to keep the per-rule `errors` and the `code` of a refusal (the shared
// interceptor would only keep the message). 401 and 403 still go through it (login, password change)
const HANDLED_ERRORS = [400, 404, 409, 503]
const REFERENCE_TTL_MS = 2 * 60 * 1000

const references = new Map()

export class BaselineApiError extends Error {
    constructor(body, status) {
        super((body && body.message) || "Something went wrong.")
        this.status = status
        this.field = body ? body.field : undefined
        this.code = body ? body.code : undefined
        this.errors = (body && body.errors) || []
    }
}

function request(method, url, data) {
    return common.getClient()
        .request({
            method,
            url,
            data,
            validateStatus: status => (status >= 200 && status < 300) || HANDLED_ERRORS.includes(status),
        })
        .then((response) => {
            if (response.status >= 300) {
                throw new BaselineApiError(response.data, response.status)
            }
            return response.data
        })
        .catch((error) => {
            if (error instanceof BaselineApiError) {
                throw error
            }
            let message = "Something went wrong."
            common.handleError(error, (text) => { message = text })
            throw new BaselineApiError({ message }, 0)
        })
}

export default {
    types() {
        return request("get", "/baselines/types")
    },
    get(fleet_id) {
        return request("get", `/baselines/fleet/${fleet_id}`)
    },
    drift(fleet_id) {
        return request("get", `/baselines/fleet/${fleet_id}/drift`)
    },
    addRules(fleet_id, rules, on_conflict = "error") {
        return request("post", `/baselines/fleet/${fleet_id}/rules`, { rules, on_conflict })
    },
    updateRule(rule_id, changes) {
        return request("put", `/baselines/rules/${rule_id}`, changes)
    },
    deleteRule(rule_id) {
        return request("delete", `/baselines/rules/${rule_id}`)
    },
    clear(fleet_id) {
        return request("delete", `/baselines/fleet/${fleet_id}`)
    },
    copy(fleet_id, from_fleet_id, mode) {
        return request("post", `/baselines/fleet/${fleet_id}/copy`, { from_fleet_id, mode })
    },
    check(fleet_id) {
        return request("post", `/baselines/fleet/${fleet_id}/check`)
    },
    // A server's settings and content, kept a short while: the rule editor and the import ask for the same one
    reference(server_id, { fresh = false } = {}) {
        const cached = references.get(server_id)
        if (!fresh && cached && Date.now() - cached.at < REFERENCE_TTL_MS) {
            return cached.promise
        }
        const promise = request("get", `/baselines/reference/${server_id}`)
        references.set(server_id, { at: Date.now(), promise })
        promise.catch(() => references.delete(server_id))
        return promise
    },
}
