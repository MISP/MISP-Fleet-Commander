import common from "./common"
import store from "@/store/index"

const urls = {
    index: `/servers/network`,
    get: `/servers/getConnection`,
    edit: `/servers/editConnection/`
}

export default {
    index(cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        // const url = `${urls.index}`
        const url = common.appendFleetIDIfDefined(`${urls.index}`)
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    get(connection, cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = `${urls.get}/${connection.source.id}/${connection.destination.Server.id}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    setPushRules(server_id, remove_server_id, payload, cb, errorCb) {
        const url = `${urls.edit}/${server_id}/${remove_server_id}`
        const pushPayload = {
            Server: {
                push_rules: JSON.stringify(payload)
            }
        }
        return common.getClient().post(url, pushPayload)
            .then((response) => {
                    cb(response.data)
                }).catch(error => {
                    common.handleError(error, errorCb)
                })
    },
    setPullRules(server_id, remove_server_id, payload, cb, errorCb) {
        const url = `${urls.edit}/${server_id}/${remove_server_id}`
        const pullPayload = {
            Server: {
                pull_rules: JSON.stringify(payload)
            }
        }
        return common.getClient().post(url, pullPayload)
            .then((response) => {
                    cb(response.data)
                }).catch(error => {
                    common.handleError(error, errorCb)
                })
    },
}
