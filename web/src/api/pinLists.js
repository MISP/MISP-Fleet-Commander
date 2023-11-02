import common from "./common"
import { baseurl } from "./apiConfig"

const urls = {
    index: `/pinlists/index`,
    add: `/pinlists/add`,
    delete: `/pinlists/delete`,
    delete_from_servers: `/pinlists/deleteFromServers`,
    refresh_all_servers: `/pinlists/refreshAllServers`,
    all_entries: `/pinlists/getAllEntries`,
    entries_from_pinned: `/pinlists/getEntriesFromPinned`,
    entries_on_server: `/pinlists/getEntriesOnServer`,
    get_avatar: `${baseurl}/pinlists/getAvatar`,
}
  
export default {
    index(cb, errorCb) {
        const url = `${urls.index}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    add(payload, cb, errorCb) {
        const url = `${urls.add}`
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    delete(entry_id, cb, errorCb) {
        const url = `${urls.delete}/${entry_id}`
        return common.getClient().delete(url)
            .then((response) => {
                cb(response.data)
            })
            .catch(error => {
                errorCb(error.data.toJSON())
            })
    },
    deleteFromServers(entry_id, cb, errorCb) {
        const url = common.appendGroupIDIfDefined(`${urls.delete_from_servers}`) + `/${entry_id}`
        return common.getClient().post(url)
            .then((response) => {
                cb(response.data)
            })
            .catch(error => {
                errorCb(error.data.toJSON())
            })
    },
    getEntriesOnServer(server_id, cb, errorCb) {
        const url = `${urls.entries_on_server}/${server_id}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    getAllEntries(cb, errorCb) {
        const url = `${urls.all_entries}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    getEntriesFromPinned(entry_id, cb, errorCb) {
        const url = `${urls.entries_from_pinned}/${entry_id}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    refreshAllServers(entry_id, cb, errorCb) {
        const url = common.appendGroupIDIfDefined(`${urls.refresh_all_servers}`) + `/${entry_id}`
        return common.getClient().post(url)
            .then((response) => {
                cb(response.data)
            })
            .catch(error => {
                debugger
                errorCb(error.data.toJSON())
            })
    },
    avatarURL() {
        const url = `${urls.get_avatar}`
        return url
    },
}
