import axios from "axios"

import store from "@/store/index"
import { baseurl } from "./apiConfig"
import Vue from "vue"
import router from "@/router"
import EventBus from '@/event-bus';

const urls = {
    searchAll: `${baseurl}/instance/searchAll`,
    githubVersion: `${baseurl}/instance/getGithubVersion`,
}

function getClient() {
    
    const client = axios.create({
        baseURL: baseurl,
        headers: {
            common: {
                Authorization: getAuthorizationHeaderValue()
            }
        }
    });
    client.interceptors.response.use(
        (response) => response,
        (error) => {
            if (error.response.status === 401) {
                return new Promise((resolve, reject) => {
                    showLoginModal(
                        () => {
                            const axios_config = Object.assign({}, error.config)
                            axios_config.headers.Authorization = getAuthorizationHeaderValue()
                            resolve(axios(axios_config))
                        },
                        (error) => {
                            console.log('Refresh login error: ', error)
                            reject(error)
                            router.push('/login')
                        }
                    )
                });
            } else if (error.response.data?.message !== undefined) {
                return Promise.reject(error.response.data.message);
            }
            return Promise.reject(error);
        }
    )
    return client
}

function getAuthorizationHeaderValue() {
    const token = store.getters["auth/access_token"]
    const token_type = store.getters["auth/access_token_type"]
    return `${token_type} ${token}`
}

function showLoginModal(successCB, errorCB) {
    EventBus.$emit('open-login-modal', successCB, errorCB);
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

function appendFleetIDIfDefined(url) {
    if (store.getters["fleets/selectedFleet"] !== null) {
        const fleetID = store.getters["fleets/selectedFleet"].id
        url += `/${fleetID}`
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
    appendFleetIDIfDefined,
    fetchGithubVersion,
    searchAll,
}
