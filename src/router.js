import Vue from "vue"
import Router from "vue-router"
import Home from "./views/home/Home.vue"
import Servers from "./views/servers/Servers.vue"
import ServerNetwork from "./views/serverNetwork/ServerNetwork.vue"

Vue.use(Router)

export default new Router({
    routes: [
        {
            path: "/",
            redirect: { name: "home" }
        },
        {
            path: "/home",
            name: "home",
            component: Home
        },
        {
            path: "/servers",
            name: "servers",
            component: Servers
        },
        {
            path: "/serverNetwork",
            name: "serverNetwork",
            component: ServerNetwork
        }
    ]
})
