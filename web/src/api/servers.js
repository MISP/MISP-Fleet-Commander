import common from "./common"
import axios from "axios"
import store from "@/store/index"

const urls = {
    testConnection: `/servers/testConnection`,
    batchTestConnection: `/servers/batchTestConnection`,
    queryInfo: `/servers/queryInfo`,
    index: `/servers/index`,
    add: `/servers/add`,
    edit: `/servers/edit`,
    delete: `/servers/delete`,
    restQuery: `/servers/restQuery`,
    getUsers: `/servers/getUsers`,
}

export default {
    index(cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = common.appendGroupIDIfDefined(`${urls.index}`)
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },

    testConnection(server_id, cb, errorCb) {
        const url = `${urls.testConnection}/${server_id}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },

    batchTestConnection(cb, errorCb) {
        const url = common.appendGroupIDIfDefined(`${urls.batchTestConnection}`)
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                console.log(error)
                errorCb(error.toJSON().message)
            })
    },

    queryInfo(payload, cb, errorCb) {
        let url = `${urls.queryInfo}/${payload.server_id}`
        url += payload.no_cache ? "/1" : ""
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },

    add(payload, cb, errorCb) {
        const url = common.appendGroupIDIfDefined(urls.add)
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response)
            })
            .catch(error => {
                console.log(error)
                errorCb(error.data.toJSON())
            })
    },

    edit(payload, cb, errorCb) {
        const url = `${urls.edit}`
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response)
            })
            .catch(error => {
                errorCb(error.data.toJSON())
            })
    },

    delete(payload, cb, errorCb) {
        const url = `${urls.delete}`
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response)
            })
            .catch(error => {
                errorCb(error.data.toJSON())
            })
    },

    restQuery(server, payload, cb, errorCb) {
        const url = `${urls.restQuery}/${server.id}`
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response.data)
            })
            .catch(error => {
                console.log(error)
                errorCb(error)
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

    queryGetUsers(server_id, cb, errorCb) {
        const url = `${urls.getUsers}/${server_id}`
        return common.getClient().get(url)
        .then((response) => {
            cb(response.data)
        }).catch(error => {
            errorCb(error.data.toJSON())
        })
    }

}
