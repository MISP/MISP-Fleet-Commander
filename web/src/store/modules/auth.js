import jwt_decode from "jwt-decode";

import router from "@/router"
import api from "@/api/auth"
import axios from "axios"

// initial state
const state = {
    access_token: localStorage.getItem('access_token'),
    access_token_type: localStorage.getItem('access_token_type'),
    decoded_access_token: JSON.parse(localStorage.getItem('decoded_access_token')) || {},
}

// getters
const getters = {
    isAuthenticated: state => {
        return !!state.access_token && !!state.decoded_access_token && state.decoded_access_token.exp > Date.now() / 1000;
    },
    user: state => state.decoded_access_token?.data?.user || null,
    access_token: (state, getter) => getter.isAuthenticated ? state.access_token : null, 
    access_token_type: (state, getter) => getter.isAuthenticated ? state.access_token_type : null, 
}

// actions
const actions = {
    authenticate({ commit }, credential) {
        return api.login(credential)
            .then((data) => {
                commit("setAccessToken", data)
            })
    },
    logout({ commit }) {
        commit("cleanAccessToken")
        localStorage.clear();
        window.location.reload()
    },
}

// mutations
const mutations = {
    setAccessToken(state, data) {
        const { access_token, token_type } = data
        state.access_token = access_token
        state.access_token_type = token_type
        state.decoded_access_token = jwt_decode(access_token)
        setLocalStorage(state)
    },
    cleanAccessToken(state) {
        state.access_token = null
        state.access_token_type = null
        state.decoded_access_token = {}
        setLocalStorage(state)
    },
}

function setLocalStorage(state) {
    localStorage.setItem('access_token', state.access_token)
    localStorage.setItem('access_token_type', state.access_token_type)
    localStorage.setItem('decoded_access_token', JSON.stringify(state.decoded_access_token))
}

function authHeader(state) {
    return `${state.access_token_type} ${state.access_token}`
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
