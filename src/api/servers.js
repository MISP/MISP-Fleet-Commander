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
        let promise  = axios.get(url)
        return promise
            .then((response) => {
                response.data.forEach((item, index) => {
                    response.data[index].status = {}
                    response.data[index].diagnostic = {}
                })
                cb(response.data)
            }).catch(error => {
                errorCb(error)
            })
    },

    testConnection(server, cb, errorCb) {
        cb()
        errorCb()
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