import store from "@/store/index"
import { baseurl } from "./apiConfig"
import axios from "axios"

const urls = {
    searchAll: `${baseurl}/instance/searchAll`,
    githubVersion: `${baseurl}/instance/getGithubVersion`,
}


function appendGroupIDIfDefined(url) {
    if (store.getters["serverGroups/selectedServerGroup"] !== null) {
        const groupID = store.getters["serverGroups/selectedServerGroup"].id
        url += `/${groupID}`
    }
    return url
}

function searchAll(searchtext, errorCb) {
    const url = `${urls.searchAll}/${searchtext}`
    return axios.get(url)
        .then((response) => {
            return response.data
        }).catch(error => {
            errorCb(error.toJSON().message)
        })
}

function fetchGithubVersion(cb, errorCb) {
    // const url = "https://api.github.com/repos/MISP/MISP/releases/latest"
    const url = urls.githubVersion
    return axios.get(url)
        .then((response) => {
            cb(response.data)
        }).catch(error => {
            console.log(error)
            if (error.data !== undefined) {
                errorCb(error.data.toJSON())
            } else {
                errorCb(error)
            }
        })
}

export default {
    appendGroupIDIfDefined,
    fetchGithubVersion,
    searchAll,
}
