import Vue from "vue"
import Router from "vue-router"
import Home from "./views/home/Home.vue"
import TheLogin from "./views/login/TheLogin.vue"
import Servers from "./views/servers/Servers.vue"
import ServerView from "./views/servers/ServerView.vue"
// import Connections from "./views/connections/Connections.vue"
import StrategicView from "./views/strategicView/StrategicView.vue"
import store from "./store/index"

Vue.use(Router)

const serverGroupSelected = (to, from, next) => {
    if (store.getters["serverGroups/selectedServerGroup"] === null) {
        if (noServerGroupPassThrough.includes(to.name)) {
            next()
        } else {
            next('home')
        }
    } else {
        next()
    }
}

const noServerGroupPassThrough = [
    "servers.view",
]

const publicRoutes = [
    '/login'
]

let router =  new Router({
    routes: [
        {
            path: "/",
            redirect: { name: "home" }
        },
        {
            path: "/login",
            name: "login",
            component: TheLogin,
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
            path: "/strategicView",
            name: "strategicView",
            component: StrategicView,
            meta: {
                requiresServerGroup: true,
                breadcrumbs: {
                    text: "Strategic View",
                    to: { name: "strategicView" },
                    icon: "fa-satellite-dish"
                }
            }
        },
        {
            path: "/users",
            name: "users",
            component: () => import("./views/users/Users.vue"),
            meta: {
                requiresServerGroup: false,
                breadcrumbs: {
                    text: "Users",
                    to: { name: "users" },
                    icon: "fa-users"
                }
            }
        }
    ]
})

router.beforeEach((to, from, next) => {

    const authRequired = !publicRoutes.includes(to.path);
    if (authRequired && !store.getters["auth/isAuthenticated"]) {
        next({ name: 'login', query: { redirect: to.fullPath } })
    }
    

    if(to.matched.some(record => record.meta.requiresServerGroup)) {
        serverGroupSelected(to, from, next)
    } else {
        next()
    }
})


export default router
