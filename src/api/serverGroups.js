import axios from "axios"

const urls = {
    index: "http://127.0.0.1:5000/serverGroups/index",
    get: "http://127.0.0.1:5000/serverGroups/get",
    add: "http://127.0.0.1:5000/serverGroups/add",
    edit: "http://127.0.0.1:5000/serverGroups/edit",
    delete: "http://127.0.0.1:5000/serverGroups/delete",
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