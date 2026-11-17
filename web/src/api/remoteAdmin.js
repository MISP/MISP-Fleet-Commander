import common from "./common"

// Requests of the Remote administration tabs (organisations, sharing groups). Answers handled here, to keep the
// `field` of a refusal and MISP's reason (502)
const HANDLED_ERRORS = [400, 404, 409, 502, 503]

export class RemoteAdminApiError extends Error {
    constructor(body, status) {
        super((body && body.message) || "Something went wrong.")
        this.status = status
        this.field = body ? body.field : undefined
    }
}

export function request(method, url, data) {
    return common.getClient()
        .request({
            method,
            url,
            data,
            validateStatus: status => (status >= 200 && status < 300) || HANDLED_ERRORS.includes(status),
        })
        .then((response) => {
            if (response.status >= 300) {
                throw new RemoteAdminApiError(response.data, response.status)
            }
            return response.data
        })
        .catch((error) => {
            if (error instanceof RemoteAdminApiError) {
                throw error
            }
            let message = "Something went wrong."
            common.handleError(error, (text) => { message = text })
            throw new RemoteAdminApiError({ message }, 0)
        })
}

export function refreshQuery(refresh) {
    return refresh ? "?refresh=1" : ""
}
