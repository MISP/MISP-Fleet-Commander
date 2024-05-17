import common from "./common"

const urls = {
    index: `/user-settings/index`,
    view: `/user-settings/view`,
    viewForUser: `/user-settings/get-for-user`,
    add: `/user-settings/add`,
    edit: `/user-settings/edit`,
    editForUser: `/user-settings/edit-for-user`,
    delete: `/user-settings/delete`,
    getSettingConfig: `/user-settings/get-setting-config`,
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
    editForUser(user_id, payload, cb, errorCb) {
        const url = `${urls.editForUser}/${user_id}`
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
    getSettingConfig(cb, errorCb) {
        const url = `${urls.getSettingConfig}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
}
