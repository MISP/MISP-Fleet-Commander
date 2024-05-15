import common from "./common"

const urls = {
    index: `/user-settings/index`,
    view: `/user-settings/view`,
    viewForUser: `/user-settings/view-for-user`,
    add: `/user-settings/add`,
    edit: `/user-settings/edit`,
    delete: `/user-settings/delete`,
}

export default {
    index(cb, errorCb) {
        const url = urls.index
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    view(user_id, cb, errorCb) {
        const url = `${urls.view}/${user_id}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    viewForUser(cb, errorCb) {
        const url = `${urls.viewForUser}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    add(payload, cb, errorCb) {
        const url = urls.add
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    edit(payload, cb, errorCb) {
        const url = urls.edit
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    delete(user_id, cb, errorCb) {
        const url = `${urls.delete}/${user_id}`
        return common.getClient().delete(url,)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
}
