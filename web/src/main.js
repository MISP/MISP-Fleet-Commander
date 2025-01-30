//import "@babel/polyfill"
//import "mutationobserver-shim"
import Vue from "vue"

import { BootstrapVue, IconsPlugin } from "bootstrap-vue"

import "bootstrap/dist/css/bootstrap.css"
import "bootstrap-vue/dist/bootstrap-vue.css"

import "@fortawesome/fontawesome-free/css/all.min.css"

import VueMoment from "vue-moment"
Vue.use(VueMoment)

// import './plugins/bootstrap-vue'
import App from "./App.vue"
import router from "./router"
import store from "./store/index"
import SocketIO from 'socket.io-client'
import VueSocketIO from 'vue-socket.io'

import { baseurl } from "@/api/apiConfig"

const socket = SocketIO(baseurl)
export const socketInstance = new VueSocketIO({
    debug: false,
    connection: socket,
    vuex: {
        store,
        actionPrefix: 'SOCKET_',
        mutationPrefix: 'SOCKET_'
    },
    // options: { path: "/my-app/" } //Optional options
});

Vue.use(socketInstance)

// Importing the global css file
import "@/assets/global.css"

import utils from "./util"
Vue.use(utils)

Vue.use(BootstrapVue)
Vue.use(IconsPlugin)
Vue.config.productionTip = false
Vue.config.performance = false

new Vue({
    router,
    store,
    render: h => h(App)
}).$mount("#app")
