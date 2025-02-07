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

const fleetSelected = (to, from, next) => {
    if (store.getters["fleets/selectedFleet"] === null) {
        if (noFleetPassThrough.includes(to.name)) {
            next()
        } else {
            next('home')
        }
    } else {
        next()
    }
}

const noFleetPassThrough = [
    "servers.view",
    "fleet.view",
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
            path: "/fleet",
            component: () => import("./components/layout/layoutWrapper.vue"),
            meta: {
                requiresFleet: true,
                breadcrumbs: {
                    text: "Fleet",
                    to: { name: "fleet.view" },
                    icon: "server"
                }
            },
            children: [
                {
                    path: ":fleet_id(\\d+)",
                    name: "fleet.view",
                    component: () => import("./views/servers/Servers.vue"),
                    props: (route) => ({ fleet_id: Number.parseInt(route.params.fleet_id, 10) || 0 }),
                    meta: {
                        requiresFleet: true,
                    }
                },
            ]
        },
        {
            path: "/servers",
            component: () => import("./components/layout/layoutWrapper.vue"),
            meta: {
                requiresFleet: true,
                breadcrumbs: {
                    text: "Fleet",
                    to: { name: "fleet.view" },
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
            ]
        },
        {
            path: "/connections",
            name: "connections",
            component: () => import("./views/connections/Connections.vue"),
            meta: {
                requiresFleet: true,
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
            component: () => import("./views/strategicView/StrategicView.vue"),
            meta: {
                requiresFleet: true,
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
                requiresFleet: false,
                breadcrumbs: {
                    text: "Commanders",
                    to: { name: "users" },
                    image_path: require('@/assets/commander.svg'),
                    image_style: "width: 1.5em; filter: invert(0.4);",
                    image_class: "d-inline-block align-top",
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

    if (to.matched.some(record => record.meta.requiresFleet)) {
        fleetSelected(to, from, next)
    } else {
        next()
    }
})


export default router
