import axios from "axios"
import store from "@/store/index"

const urls = {
    testConnection: "http://127.0.0.1:5000/servers/testConnection",
    batchTestConnection: "http://127.0.0.1:5000/servers/batchTestConnection",
    queryInfo: "http://127.0.0.1:5000/servers/queryInfo",
    index: "http://127.0.0.1:5000/servers/index",
    add: "http://127.0.0.1:5000/servers/add",
    edit: "http://127.0.0.1:5000/servers/edit",
    delete: "http://127.0.0.1:5000/servers/delete",
    restQuery: "http://127.0.0.1:5000/servers/restQuery",
    getUsers: "http://127.0.0.1:5000/servers/getUsers"
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

    testConnection(server, cb, errorCb) {
        const url = `${urls.testConnection}/${server.id}`
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
        let url = `${urls.queryInfo}/${payload.server.id}`
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
                errorCb(error.data.toJSON())
            })
    },

    add(payload, cb, errorCb) {
        const url = appendGroupIDIfDefined(urls.add)
        return axios.post(url, payload)
            .then((response) => {
                cb(response.data)
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
                cb(response.data)
            })
            .catch(error => {
                errorCb(error.data.toJSON())
            })
    },

    delete(payload, cb, errorCb) {
        const url = `${urls.delete}`
        return axios.post(url, payload)
            .then((response) => {
                cb(response.data)
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