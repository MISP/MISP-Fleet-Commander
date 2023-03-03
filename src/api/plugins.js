import { baseurl } from "./apiConfig"
import common from "./common"
import axios from "axios"

const urls = {
    index: `${baseurl}/plugins/index`,
    getIndexValues: `${baseurl}/plugins/indexValues`,
}
  
export default {
    index(cb, errorCb) {
        const url = `${urls.index}`
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    getIndexValues(cb, errorCb) {
        const url = common.appendGroupIDIfDefined(`${urls.getIndexValues}`)
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
}
