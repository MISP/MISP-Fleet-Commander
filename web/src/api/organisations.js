import common from "./common"

// Answers handled here, to keep the `field` of a refusal and MISP's reason (502)
const HANDLED_ERRORS = [400, 404, 409, 502, 503]

export class OrganisationApiError extends Error {
    constructor(body, status) {
        super((body && body.message) || "Something went wrong.")
        this.status = status
        this.field = body ? body.field : undefined
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
                throw new OrganisationApiError(response.data, response.status)
            }
            return response.data
        })
        .catch((error) => {
            if (error instanceof OrganisationApiError) {
                throw error
            }
            let message = "Something went wrong."
            common.handleError(error, (text) => { message = text })
            throw new OrganisationApiError({ message }, 0)
        })
}

const base = "/server-management/organisations"

export default {
    // {server_id, fetched_at, cached, organisations}
    index(server_id, { refresh = false } = {}) {
        return request("get", `${base}/${server_id}${refresh ? "?refresh=1" : ""}`)
    },
    // {compared, unavailable, organisations: {uuid: {same, renamed, other_uuid}}}
    fleet(server_id, { refresh = false } = {}) {
        return request("get", `${base}/${server_id}/fleet${refresh ? "?refresh=1" : ""}`)
    },
    add(server_id, fields) {
        return request("post", `${base}/${server_id}/add`, fields)
    },
    edit(server_id, org_id, changes) {
        return request("post", `${base}/${server_id}/edit/${org_id}`, changes)
    },
    // 202 {job_id, job}
    copy(server_id, { uuid, server_ids, local }) {
        return request("post", `${base}/${server_id}/copy`, { uuid, server_ids, local })
    },
}
