import axios from "axios"

import store from "@/store/index"
import { baseurl } from "./apiConfig"

const urls = {
    searchAll: `${baseurl}/instance/searchAll`,
    githubVersion: `${baseurl}/instance/getGithubVersion`,
}

function getClient() {
    const token = store.getters["auth/access_token"]
    const token_type = store.getters["auth/access_token_type"]
    const client = axios.create({
        baseURL: baseurl,
        headers: {
            common: {
                Authorization: `${token_type} ${token}`
            }
        }
    });
    client.interceptors.response.use(
        (response) => response,
        (error) => {
            if (error.response.status === 401) {
                return Promise.reject({ message: 'Authentication required' });
            } else if (error.response.data?.message !== undefined) {
                return Promise.reject(error.response.data.message);
            }
            return Promise.reject(error);
        }
    )
    return client
}

function showLoginModal() {
    store.commit('auth/toggleShowLoginPage', true)
}

function handleError(error, errorCb) {
    if (error !== undefined) {
        if (error.message) {
            if (error._showToLoginPage) {
                showGoToLoginPageToast(error)
            } else {
                errorCb(error.message)
            }
        } else {
            errorCb(error.toJSON().message)
        }
    }
    errorCb('Something went wrong.')
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
    return this.getClient().get(url)
        .then((response) => {
            return response.data
        }).catch(error => {
            handleError(error, errorCb)
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
    getClient,
    handleError,
    appendGroupIDIfDefined,
    fetchGithubVersion,
    searchAll,
}
