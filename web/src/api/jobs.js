import common from "./common"

const urls = {
    jobs: `/jobs`,
}

export default {
    create(payload, cb, errorCb) {
        return common.getClient().post(urls.jobs, payload)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    index(params, cb, errorCb) {
        return common.getClient().get(urls.jobs, { params })
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    get(job_id, cb, errorCb) {
        return common.getClient().get(`${urls.jobs}/${encodeURIComponent(job_id)}`)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    cancel(job_id, cb, errorCb) {
        return common.getClient().post(`${urls.jobs}/${encodeURIComponent(job_id)}/cancel`)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    retry(job_id, only_failed, cb, errorCb) {
        return common.getClient().post(`${urls.jobs}/${encodeURIComponent(job_id)}/retry`, { only_failed })
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
}
