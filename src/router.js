import Vue from "vue"
import Router from "vue-router"
import Home from "./views/home/Home.vue"
import Servers from "./views/servers/Servers.vue"
import ServerView from "./views/servers/ServerView.vue"
// import Connections from "./views/connections/Connections.vue"
import ServerNetwork from "./views/serverNetwork/ServerNetwork.vue"
import store from "./store/index"

Vue.use(Router)

const serverGroupSelected = (to, from, next) => {
    if (store.getters["serverGroups/selectedServerGroup"] === null) {
        store.dispatch("serverGroups/selectServerGroupFromServerId", to.params.server_id).then(() => {
            next()
        }).catch(() => {
            next("/home")
        })
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
            component: Home,
            meta: {
                breadcrumbs: {
                    text: "Home",
                    to: { name: "home" },
                    icon: "home"
                }
            }
        },
        {
            path: "/servers",
            component: () => import("./components/layout/layoutWrapper.vue"),
            meta: {
                requiresServerGroup: true,
                breadcrumbs: {
                    text: "Servers",
                    to: { name: "servers.index" },
                    icon: "server"
                }
            },
            children: [
                {
                    path: ":server_id(\\d+)",
                    name: "servers.view",
                    component: () => import("./views/servers/ServerView.vue"),
                    //props: true,
                    props: (route) => ({server_id: Number.parseInt(route.params.server_id, 10) || 0}),
                    meta: {
                        breadcrumbs: {
                            textGetter: "server_id",
                            to: { name: "servers.view" },
                        }
                    }
                },
                {
                    path: "",
                    name: "servers.index",
                    component: () => import("./views/servers/Servers.vue"),
                    meta: {
                        requiresServerGroup: true,
                    }
                },
            ]
        },
        {
            path: "/connections",
            name: "connections",
            // component: Connections,
            component: () => import("./views/connections/Connections.vue"),
            meta: {
                requiresServerGroup: true,
                breadcrumbs: {
                    text: "Connections",
                    to: { name: "connections" },
                    icon: "network-wired"
                }
            }
        },
        {
            path: "/serverNetwork",
            name: "serverNetwork",
            component: ServerNetwork,
            meta: {
                requiresServerGroup: true,
                breadcrumbs: {
                    text: "Server Networks",
                    to: { name: "serverNetwork" },
                    icon: "fa-project-diagram"
                }
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
