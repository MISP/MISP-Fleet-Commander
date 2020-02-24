import axios from "axios"

const urls = {
    testConnection: "http://127.0.0.1:5000/servers/testConnection",
    queryDiagnostic: "http://127.0.0.1:5000/servers/queryDiagnostic",
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
                errorCb(error)
            })
    },

    testConnection(server, cb, errorCb) {
        const url = `${urls.testConnection}/${server.id}`
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                console.log(error)
                errorCb(error)
            })
    },

    queryDiagnostic(server, cb, errorCb) {
        cb(server)
        errorCb()
    },

    add(server, cb, errorCb) {
        cb(server)
        errorCb()
    },

    edit(server, cb, errorCb) {
        cb(server)
        errorCb()
    },

    delete(server, cb, errorCb) {
        cb(server)
        errorCb()
    }
}