import common from "./common"
import store from "@/store/index"

const urls = {
    index: `/servers/network`,
    get: `/servers/getConnection`
}

export default {
    index(cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        // const url = `${urls.index}`
        const url = common.appendGroupIDIfDefined(`${urls.index}`)
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    get(connection, cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = `${urls.get}/${connection.source.id}/${connection.destination.Server.id}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
}
