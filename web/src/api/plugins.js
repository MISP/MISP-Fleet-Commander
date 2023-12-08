import common from "./common"
import axios from "axios"

const urls = {
    index: `/plugins/index`,
    getIndexValues: `/plugins/indexValues`,
    getViewValues: `/plugins/viewValues`,
    notifications: `/plugins/notifications`,
    submitAction: `/plugins/doAction`,
}


export default {
    index(cb, errorCb) {
        const url = `${urls.index}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    getIndexValues(cb, errorCb) {
        const url = common.appendFleetIDIfDefined(`${urls.getIndexValues}`)
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    getViewValues(serverID, cb, errorCb) {
        const url = `${urls.getViewValues}/${serverID}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    submitAction(serverID, pluginID, data) {
        const url = `${urls.submitAction}/${serverID}/${pluginID}`
        return common.getClient().post(url, data)
    },
    getNotifications(serverID, cb, errorCb) {
        const url = `${urls.notifications}/${serverID}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
}
