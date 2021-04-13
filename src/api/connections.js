import axios from "axios"
import store from "@/store/index"

const urls = {
    index: "http://127.0.0.1:5000/servers/network",
    get: "http://127.0.0.1:5000/servers/getConnection",
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
        // const url = `${urls.index}`
        const url = appendGroupIDIfDefined(`${urls.index}`)
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    get(connection, cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = `${urls.get}/${connection.source.id}/${connection.destination.Server.id}`
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
}