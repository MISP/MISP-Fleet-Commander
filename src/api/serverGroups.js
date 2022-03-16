import { baseurl } from "./apiConfig"
import axios from "axios"

const urls = {
    index: `${baseurl}/serverGroups/index`,
    get: `${baseurl}/serverGroups/get`,
    add: `${baseurl}/serverGroups/add`,
    edit: `${baseurl}/serverGroups/edit`,
    delete: `${baseurl}/serverGroups/delete`,
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
    get(group, cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = `${urls.get}/${group.id}`
        return axios.get(url)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
    add(group, cb, errorCb) {
        // const url = `${url.index}?page=${ctx.currentPage}&size=${ctx.perPage}`
        const url = `${urls.add}`
        return axios.post(url, group)
            .then((response) => {
                cb(response.data)
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
}
