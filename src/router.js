import Vue from "vue"
import Router from "vue-router"
import Home from "./views/home/Home.vue"
import Servers from "./views/servers/Servers.vue"
import Connections from "./views/connections/Connections.vue"
import ServerNetwork from "./views/serverNetwork/ServerNetwork.vue"
import store from "./store/index"

Vue.use(Router)

const serverGroupSelected = (to, from, next) => {
    if (store.getters["serverGroups/selectedServerGroup"] === null) {
        next("/home")
    } else {
        next()
    }
}

let router =  new Router({
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
            component: Servers,
            meta: {
                requiresServerGroup: true
            }
        },
        {
            path: "/connections",
            name: "connections",
            component: Connections,
            meta: {
                requiresServerGroup: true
            }
        },
        {
            path: "/serverNetwork",
            name: "serverNetwork",
            component: ServerNetwork,
            meta: {
                requiresServerGroup: true
            }
        }
    ]
})

router.beforeEach((to, from, next) => {
    if(to.matched.some(record => record.meta.requiresServerGroup)) {
        serverGroupSelected(to, from, next)
    } else {
        next()
    }
})


export default router
