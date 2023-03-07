import { baseurl } from "./apiConfig"
import common from "./common"
import axios from "axios"

const urls = {
    index: `${baseurl}/plugins/index`,
    getIndexValues: `${baseurl}/plugins/indexValues`,
    getViewValues: `${baseurl}/plugins/viewValues`,
    notifications: `${baseurl}/plugins/notifications`,
    submitAction: `${baseurl}/plugins/doAction`,
}
  
export default {
    index(cb, errorCb) {
        const url = `${urls.index}`
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    getIndexValues(cb, errorCb) {
        const url = common.appendGroupIDIfDefined(`${urls.getIndexValues}`)
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    getViewValues(serverID, cb, errorCb) {
        const url = `${urls.getViewValues}/${serverID}`
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    submitAction(serverID, pluginID, data) {
        const url = `${urls.submitAction}/${serverID}/${pluginID}`
        return axios.post(url, data)
    },
    getNotifications(serverID, cb, errorCb) {
        const url = `${urls.notifications}/${serverID}`
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
}
