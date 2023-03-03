import store from "@/store/index"
import { baseurl } from "./apiConfig"
import axios from "axios"

const urls = {
    searchAll: `${baseurl}/instance/searchAll`,
}


function appendGroupIDIfDefined(url) {
    if (store.getters["serverGroups/selectedServerGroup"] !== null) {
        const groupID = store.getters["serverGroups/selectedServerGroup"].id
        url += `/${groupID}`
    }
    return url
}


export default {
    appendGroupIDIfDefined,
    searchAll(searchtext, errorCb) {
        const url = `${urls.searchAll}/${searchtext}`
        return axios.get(url)
            .then((response) => {
                return response.data
            }).catch(error => {
                errorCb(error.toJSON().message)
            })
    },
}
