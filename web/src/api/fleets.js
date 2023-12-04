import common from "./common"

const urls = {
    index: `/fleets/index`,
    get: `/fleets/get`,
    add: `/fleets/add`,
    edit: `/fleets/edit`,
    delete: `/fleets/delete`,
    getFromServerId: `/fleets/getFromServerId`,
}
  
export default {
    index(cb, errorCb) {
        const url = `${urls.index}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    get(fleet, cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = `${urls.get}/${fleet.id}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    add(fleet, cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = `${urls.add}`
        return common.getClient().post(url, fleet)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    delete(fleet, cb, errorCb) {
        const url = `${urls.delete}/${fleet.id}`
        return common.getClient().delete(url, fleet)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    getFromServerId(serverId, cb, errorCb) {
        const url = `${urls.getFromServerId}/${serverId}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
}
