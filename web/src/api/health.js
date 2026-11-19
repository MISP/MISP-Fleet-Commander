import common from "./common"

const urls = {
    issues: `/health/issues`,
    summary: `/health/summary`,
    ack: `/health/ack`,
    ackBulk: `/health/ack/bulk`,
    unackBulk: `/health/unack/bulk`,
}

export default {
    issues(params, cb, errorCb) {
        return common.getClient().get(urls.issues, { params })
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    summary(cb, errorCb) {
        return common.getClient().get(urls.summary)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    acknowledge(payload, cb, errorCb) {
        return common.getClient().post(urls.ack, payload)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    // payload: { issue_ids, until?, note? } -> { acknowledged: [issue], skipped: [{ issue_id, message }] }
    acknowledgeMany(payload, cb, errorCb) {
        return common.getClient().post(urls.ackBulk, payload)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    // -> { unacknowledged: [issue_id], skipped: [{ issue_id, message }] }
    unacknowledgeMany(issue_ids, cb, errorCb) {
        return common.getClient().post(urls.unackBulk, { issue_ids })
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    unacknowledge(issue_id, cb, errorCb) {
        return common.getClient().delete(`${urls.ack}/${encodeURIComponent(issue_id)}`)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
}
