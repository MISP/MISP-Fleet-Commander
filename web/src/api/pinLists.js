import common from "./common"
import { baseurl } from "./apiConfig"

const urls = {
    index: `/pinlists/index`,
    add: `/pinlists/add`,
    delete: `/pinlists/delete`,
    delete_from_server: `/pinlists/deleteFromServer`,
    delete_from_servers: `/pinlists/deleteFromServers`,
    refresh_server_entry: `/pinlists/refreshServerEntry`,
    refresh_all_servers: `/pinlists/refreshAllServers`,
    all_entries: `/pinlists/getAllEntries`,
    all_entries_from_server: `/pinlists/getAllEntriesFromServer`,
    entries_from_pinned: `/pinlists/getEntriesFromPinned`,
    entries_on_server: `/pinlists/getEntriesOnServer`,
    publish_event_on_server: `/pinlists/publishEventOnServer`,
    get_avatar: `${baseurl}/pinlists/getAvatar`,
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
    add(payload, cb, errorCb) {
        const url = `${urls.add}`
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
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
    deleteFromServer(entry_id, server_id, cb, errorCb) {
        const url = `${urls.delete_from_server}/${server_id}/${entry_id}`
        return common.getClient().post(url)
            .then((response) => {
                cb(response.data)
            })
            .catch(error => {
                errorCb(error.data.toJSON())
            })
    },
    deleteFromServers(entry_id, cb, errorCb) {
        const url = common.appendFleetIDIfDefined(`${urls.delete_from_servers}`) + `/${entry_id}`
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
                common.handleError(error, errorCb)
            })
    },
    getAllEntries(cb, errorCb) {
        const url = `${urls.all_entries}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    getAllFromServer(server_id, cb, errorCb) {
        const url = `${urls.all_entries_from_server}/${server_id}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    getEntriesFromPinned(entry_id, cb, errorCb) {
        const url = `${urls.entries_from_pinned}/${entry_id}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    refreshServerEntry(entry_id, server_id, cb, errorCb) {
        const url = `${urls.refresh_server_entry}/${server_id}/${entry_id}`
        return common.getClient().post(url)
            .then((response) => {
                cb(response.data)
            })
            .catch(error => {
                common.handleError(error, errorCb)
            })
    },
    refreshAllServers(entry_id, cb, errorCb) {
        const url = common.appendFleetIDIfDefined(`${urls.refresh_all_servers}`) + `/${entry_id}`
        return common.getClient().post(url)
        .then((response) => {
            cb(response.data)
        })
        .catch(error => {
            common.handleError(error, errorCb)
        })
    },
    publishEventOnServer(entry_id, server_id, cb, errorCb) {
        const url = `${urls.publish_event_on_server}/${server_id}/${entry_id}`
        return common.getClient().post(url)
            .then((response) => {
                cb(response.data)
            })
            .catch(error => {
                common.handleError(error, errorCb)
            })
    },
    avatarURL() {
        const url = `${urls.get_avatar}`
        return url
    },
}
