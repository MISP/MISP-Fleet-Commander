import common from "./common"
import axios from "axios"
import store from "@/store/index"

const urls = {
    testConnection: `/servers/testConnection`,
    batchTestConnection: `/servers/batchTestConnection`,
    queryInfo: `/servers/queryInfo`,
    index: `/servers/index`,
    get: `/servers/get`,
    add: `/servers/add`,
    edit: `/servers/edit`,
    delete: `/servers/delete`,
    restQuery: `/servers/restQuery`,
    getUsers: `/servers/getUsers`,
    getUsageDashboardConfig: `/servers/getUsageDashboardConfig`,
    getInstancePicture: `/servers/getInstancePicture`,
    batchTest: `/servers/batchTest`,
    discoverConnected: `/servers/discoverConnected`,
    syncOvertime: `/servers/syncOvertime`,
}

export default {
    index(cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = common.appendFleetIDIfDefined(`${urls.index}`)
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },

    testConnection(server_id, cb, errorCb) {
        const url = `${urls.testConnection}/${server_id}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },

    batchTestConnection(cb, errorCb) {
        const url = common.appendFleetIDIfDefined(`${urls.batchTestConnection}`)
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                console.log(error)
                common.handleError(error, errorCb)
            })
    },

    queryInfo(payload, cb, errorCb) {
        let url = `${urls.queryInfo}/${payload.server_id}`
        url += payload.no_cache ? "/1" : ""
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },

    add(payload, cb, errorCb) {
        const url = common.appendFleetIDIfDefined(urls.add)
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response)
            })
            .catch(error => {
                common.handleError(error, errorCb)
            })
    },

    edit(payload, cb, errorCb) {
        const url = `${urls.edit}`
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response)
            })
            .catch(error => {
                common.handleError(error, errorCb)
            })
    },

    delete(payload, cb, errorCb) {
        const url = `${urls.delete}`
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response)
            })
            .catch(error => {
                common.handleError(error, errorCb)
            })
    },

    restQuery(server, payload, cb, errorCb) {
        const url = `${urls.restQuery}/${server.id}`
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response.data)
            })
            .catch(error => {
                common.handleError(error, errorCb)
            })
    },

    batchRestQuery(server_ids, payload) {
        let allPromises = []
        server_ids.forEach(server_id => {
            const url = `${urls.restQuery}/${server_id}`
            const query = common.getClient().post(url, payload)
            allPromises.push(query)
        });
        return Promise.all(allPromises)
    },

    batchTest(payload) {
        // payload: list of `{id}` (saved server) or `{url, authkey, skip_ssl}` (not saved yet)
        return common.getClient().post(urls.batchTest, payload)
            .then((response) => response.data)
    },

    discoverConnected(root_server_id) {
        return common.getClient().post(urls.discoverConnected, { root_server_id })
            .then((response) => response.data)
    },

    // Pulls and pushes of the last days per sync server, read from the server's MISP logs (cached by the backend
    // unless `refresh`)
    syncOvertime(server_id, refresh = false) {
        const url = `${urls.syncOvertime}/${server_id}${refresh ? "?refresh=1" : ""}`
        return common.getClient().get(url)
            .then((response) => response.data)
    },

    queryGetUsers(server_id, cb, errorCb) {
        const url = `${urls.getUsers}/${server_id}`
        return common.getClient().get(url)
        .then((response) => {
            cb(response.data)
        }).catch(error => {
            common.handleError(error, errorCb)
        })
    },

    getUsageDashboardConfig(cb, errorCb) {
        const url = `${urls.getUsageDashboardConfig}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },

    get(server_id, cb, errorCb) {
        return common.getClient().get(`${urls.get}/${server_id}`)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    getInstancePicture(server_id, cb, errorCb) {
        const url = `${urls.getInstancePicture}/${server_id}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },

}
