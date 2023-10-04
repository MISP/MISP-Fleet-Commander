import common from "./common"

const urls = {
    index: `/users/index`,
    get: `/users/get`,
    add: `/users/add`,
    edit: `/users/edit`,
    delete: `/users/delete`,
}

export default {
    index(cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = urls.index
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    get(cb, errorCb) {
        const url = urls.get
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    add(payload, cb, errorCb) {
        const url = urls.add
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    edit(payload, cb, errorCb) {
        const url = urls.edit
        return common.getClient().post(url, payload)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    delete(user_id, cb, errorCb) {
        const url = `${urls.delete}/${user_id}`
        return common.getClient().delete(url,)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
}
