import { baseurl } from "./apiConfig"
import axios from "axios"
import store from "@/store/index"

const urls = {
    testConnection: `${baseurl}/servers/testConnection`,
    batchTestConnection: `${baseurl}/servers/batchTestConnection`,
    queryInfo: `${baseurl}/servers/queryInfo`,
    index: `${baseurl}/servers/index`,
    add: `${baseurl}/servers/add`,
    edit: `${baseurl}/servers/edit`,
    delete: `${baseurl}/servers/delete`,
    restQuery: `${baseurl}/servers/restQuery`,
    getUsers: `${baseurl}/servers/getUsers`
}

const appendGroupIDIfDefined = (url) => {
    if (store.getters["serverGroups/selectedServerGroup"] !== null) {
        const groupID = store.getters["serverGroups/selectedServerGroup"].id
        url += `/${groupID}`
    }
    return url
}
  
export default {
    index(cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = appendGroupIDIfDefined(`${urls.index}`)
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },

    testConnection(server_id, cb, errorCb) {
        const url = `${urls.testConnection}/${server_id}`
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },

    batchTestConnection(cb, errorCb) {
        const url = appendGroupIDIfDefined(`${urls.batchTestConnection}`)
        return axios.get(url)
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
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },

    fetchGithubVersion(cb, errorCb) {
        const url = "https://api.github.com/repos/MISP/MISP/releases/latest"
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                console.log(error)
                if (error.data !== undefined) {
                    errorCb(error.data.toJSON())
                } else {
                    errorCb(error)
                }
            })
    },

    add(payload, cb, errorCb) {
        const url = appendGroupIDIfDefined(urls.add)
        return axios.post(url, payload)
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
        return axios.post(url, payload)
            .then((response) => {
                cb(response)
            })
            .catch(error => {
                errorCb(error.data.toJSON())
            })
    },

    delete(payload, cb, errorCb) {
        const url = `${urls.delete}`
        return axios.post(url, payload)
            .then((response) => {
                cb(response)
            })
            .catch(error => {
                errorCb(error.data.toJSON())
            })
    },

    restQuery(server, payload, cb, errorCb) {
        const url = `${urls.restQuery}/${server.id}`
        return axios.post(url, payload)
            .then((response) => {
                cb(response.data)
            })
            .catch(error => {
                console.log(error)
                errorCb(error)
            })
    },

    queryGetUsers(server_id, cb, errorCb) {
        const url = `${urls.getUsers}/${server_id}`
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.data.toJSON())
            })
    }

}
