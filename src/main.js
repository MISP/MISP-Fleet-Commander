import "@babel/polyfill"
import "mutationobserver-shim"
import Vue from "vue"

import { BootstrapVue, IconsPlugin } from 'bootstrap-vue'

import "bootstrap/dist/css/bootstrap.css"
import "bootstrap-vue/dist/bootstrap-vue.css"

import "@fortawesome/fontawesome-free/css/all.min.css"

// import './plugins/bootstrap-vue'
import App from "./App.vue"
import router from "./router"
import store from "./store"

// Importing the global css file
import "@/assets/global.css"

import utils from "./util"
Vue.use(utils)

Vue.use(BootstrapVue)
Vue.use(IconsPlugin)
Vue.config.productionTip = false

new Vue({
    router,
    store,
    render: h => h(App)
}).$mount("#app")
