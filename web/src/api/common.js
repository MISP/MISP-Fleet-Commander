import axios from "axios"

import store from "@/store/index"
import { baseurl } from "./apiConfig"
import Vue from "vue"
import router from "@/router"
import EventBus from '@/event-bus';

const urls = {
    searchAll: `${baseurl}/instance/searchAll`,
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
            } else if (error.response.status === 403 && error.response.data?.password_change_required) {
                if (router.currentRoute.name !== "change-password") {
                    router.push({ name: "change-password", query: { redirect: router.currentRoute.fullPath } }).catch(() => {})
                }
                return Promise.reject(error.response.data.message)
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
    // The client's interceptor rejects with the server's message when there is one
    if (typeof error === "string") {
        errorCb(error)
        return
    }
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

// Images served by the API need the Authorization header, which <img src> cannot send: fetch them and
// return an object URL. Callers release it with URL.revokeObjectURL once the image is not displayed anymore.
function fetchImageObjectURL(url) {
    return getClient().get(url, { responseType: "blob" })
        .then((response) => URL.createObjectURL(response.data))
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

export default {
    getClient,
    handleError,
    fetchImageObjectURL,
    appendFleetIDIfDefined,
    searchAll,
}
