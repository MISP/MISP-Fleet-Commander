import axios from "axios"

const urls = {
    testConnection: "http://127.0.0.1:5000/servers/testConnection",
    batchTestConnection: "http://127.0.0.1:5000/servers/batchTestConnection",
    queryInfo: "http://127.0.0.1:5000/servers/queryInfo",
    index: "http://127.0.0.1:5000/servers/index",
    add: "http://127.0.0.1:5000/servers/add",
    edit: "http://127.0.0.1:5000/servers/edit",
    delete: "http://127.0.0.1:5000/servers/delete",
}
  
export default {
    index(cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = `${urls.index}`
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
        const url = `${urls.batchTestConnection}`
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
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
        const url = urls.add
        return axios.post(url, payload)
            .then((response) => {
                cb(response.data)
            })
            .catch(error => {
                console.log(error)
                errorCb(error.data.toJSON())
            })
    },

    edit(server, cb, errorCb) {
        cb(server)
        errorCb()
    },

    delete(payload, cb, errorCb) {
        const url = urls.delete
        return axios.post(url, payload)
            .then((response) => {
                cb(response.data)
            })
            .catch(error => {
                console.log(error)
                errorCb(error.data.toJSON())
            })
    }
}