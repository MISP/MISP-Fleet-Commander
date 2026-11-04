import common from "./common"

const urls = {
    get: `/servers/getNotifications`,
}
  
export default {
    get(server_id, cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = `${urls.get}/${server_id}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
}
