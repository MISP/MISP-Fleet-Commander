import common from "./common"

const urls = {
    disable: `/server-management/user/disable`,
    enable: `/server-management/user/enable`,
    setPassword: `/server-management/user/set-password`,
    resetPassword: `/server-management/user/reset-password`,
    genAuthkey: `/server-management/user/gen-authkey`,
    addUser: `/server-management/user/add`,
}

export default {
    disable(server_id, user_id, cb, errorCb) {
        const url = `${urls.disable}/${server_id}/${user_id}`
        return common.getClient().post(url, {})
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    enable(server_id, user_id, cb, errorCb) {
        const url = `${urls.enable}/${server_id}/${user_id}`
        return common.getClient().post(url, {})
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    setPassword(server_id, payload, cb, errorCb) {
        const url = `${urls.setPassword}/${server_id}`
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    resetPassword(server_id, user_id, payload, cb, errorCb) {
        const url = `${urls.resetPassword}/${server_id}/${user_id}`
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    genAuthkey(server_id, user_id, cb, errorCb) {
        const url = `${urls.genAuthkey}/${server_id}/${user_id}`
        return common.getClient().post(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    addUser(server_id, payload, cb, errorCb) {
        const url = `${urls.addUser}/${server_id}`
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
}
