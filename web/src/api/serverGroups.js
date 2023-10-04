import common from "./common"

const urls = {
    index: `/serverGroups/index`,
    get: `/serverGroups/get`,
    add: `/serverGroups/add`,
    edit: `/serverGroups/edit`,
    delete: `/serverGroups/delete`,
    getFromServerId: `/serverGroups/getFromServerId`,
}
  
export default {
    index(cb, errorCb) {
        const url = `${urls.index}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    get(group, cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = `${urls.get}/${group.id}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    add(group, cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = `${urls.add}`
        return common.getClient().post(url, group)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    delete(group, cb, errorCb) {
        const url = `${urls.delete}/${group.id}`
        return common.getClient().delete(url, group)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    getFromServerId(serverId, cb, errorCb) {
        const url = `${urls.getFromServerId}/${serverId}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
}
