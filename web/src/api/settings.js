import common from "./common"

const urls = {
    index: `/instance/settings/index`,
    get: `/instance/settings/get`,
    edit: `/instance/settings/edit`,
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
    get(setting_name, cb, errorCb) {
        const url = `${urls.get}/${setting_name}`
        return common.getClient().get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
    edit(payload, cb, errorCb) {
        const setting_name = payload.name
        const payload_to_send = {value: payload.value}
        const url = `${urls.edit}/${setting_name}`
        return common.getClient().post(url, payload_to_send)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                common.handleError(error, errorCb)
            })
    },
}
