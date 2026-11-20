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
    // The fleet named in the URL wins over the one selected, so that links and bookmarks open the fleet they name
    const wanted = Number.parseInt(to.params.fleet_id, 10)
    const selected = store.getters["fleets/selectedFleet"]
    if (!Number.isNaN(wanted) && (selected === null || selected.id !== wanted)) {
        store.dispatch("fleets/selectFleet", { data: { id: wanted }, redirect: false })
            .then(() => {
                store.dispatch("servers/fetchServers", { force: true })
                next()
            })
            .catch(() => {
                next({ name: "home" })
            })
        return
    }
    if (selected === null) {
        if (noFleetPassThrough.includes(to.name)) {
            if (
                (to.name == 'fleet.view' && to.params.fleet_id !== undefined) ||
                (to.name == 'servers.view' && to.params.server_id !== undefined)
            ) {
                next()
            } else {
                next('home')
            }
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
            path: "/change-password",
            name: "change-password",
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
                    path: ":fleet_id(\\d+)?",
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
            path: "/attention",
            name: "attention",
            component: () => import("./views/attention/Attention.vue"),
            meta: {
                requiresFleet: false,
                breadcrumbs: {
                    text: "Needs attention",
                    to: { name: "attention" },
                    icon: "heart-pulse"
                }
            }
        },
        {
            path: "/jobs",
            // Both pages have their own layout: the parent only gives the job page its "Jobs" breadcrumb. It passes
            // on App's listeners, so that the pages' `update:layout` still reaches App
            component: {
                name: "JobsRoot",
                render(h) {
                    return h("router-view", { on: this.$listeners })
                },
            },
            meta: {
                requiresFleet: false,
                breadcrumbs: {
                    text: "Jobs",
                    to: { name: "jobs" },
                    icon: "list-check"
                }
            },
            children: [
                {
                    path: "",
                    name: "jobs",
                    component: () => import("./views/jobs/Jobs.vue"),
                    meta: {
                        requiresFleet: false,
                    }
                },
                {
                    path: ":job_id([0-9a-f-]{36})",
                    name: "jobs.view",
                    component: () => import("./views/jobs/JobView.vue"),
                    props: (route) => ({ job_id: route.params.job_id }),
                    meta: {
                        requiresFleet: false,
                        breadcrumbs: {
                            text: "Job",
                            to: { name: "jobs.view" },
                        }
                    }
                },
            ]
        },
        {
            path: "/query",
            component: {
                name: "QueryRoot",
                render(h) {
                    return h("router-view", { on: this.$listeners })
                },
            },
            meta: {
                requiresFleet: false,
                breadcrumbs: {
                    text: "Query",
                    to: { name: "query" },
                    icon: "magnifying-glass"
                }
            },
            children: [
                {
                    path: "saved",
                    component: {
                        name: "SavedQueriesRoot",
                        render(h) {
                            return h("router-view", { on: this.$listeners })
                        },
                    },
                    meta: {
                        requiresFleet: false,
                        breadcrumbs: {
                            text: "Saved queries",
                            to: { name: "query.saved" },
                        }
                    },
                    children: [
                        {
                            path: "",
                            name: "query.saved",
                            component: () => import("./views/query/SavedQueries.vue"),
                            meta: {
                                requiresFleet: false,
                            }
                        },
                        {
                            path: ":saved_id(\\d+)",
                            name: "query.saved.view",
                            component: () => import("./views/query/SavedQueryView.vue"),
                            props: (route) => ({ saved_id: Number.parseInt(route.params.saved_id, 10) }),
                            meta: {
                                requiresFleet: false,
                                breadcrumbs: {
                                    text: "Saved query",
                                    to: { name: "query.saved.view" },
                                }
                            }
                        },
                    ]
                },
                {
                    // A statement to run on many servers (`?fleet=<id>` or `?servers=1,2` chooses them, `?saved=<id>`
                    // opens a saved query), or a run's answers
                    path: ":job_id([0-9a-f-]{36})?",
                    name: "query",
                    component: () => import("./views/query/QueryPage.vue"),
                    props: (route) => ({ job_id: route.params.job_id || null }),
                    meta: {
                        requiresFleet: false,
                    }
                },
            ]
        },
        {
            path: "/baselines",
            name: "baselines",
            component: () => import("./views/baselines/BaselineLibrary.vue"),
            meta: {
                requiresFleet: false,
                breadcrumbs: {
                    text: "Baselines",
                    to: { name: "baselines" },
                    icon: "ruler-combined"
                }
            }
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
            component: () => import("./components/layout/layoutWrapperStretch.vue"),
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
                    path: ":fleet_id(\\d+)?",
                    name: "strategicView",
                    component: () => import("./views/strategicView/StrategicView.vue"),
                    props: (route) => ({ fleet_id: Number.parseInt(route.params.fleet_id, 10) || 0 }),
                    meta: {
                        requiresFleet: true,
                        breadcrumbs: {
                            text: "Strategic View",
                            to: { name: "strategicView" },
                            icon: "fa-satellite-dish"
                        }
                    }
                }
            ]
        },
        {
            path: "/users",
            name: "users",
            component: () => import("./views/users/Users.vue"),
            meta: {
                requiresFleet: false,
                requiresAdmin: true,
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
        return
    }
    if (authRequired && to.name !== 'change-password' && store.getters["auth/mustChangePassword"]) {
        next({ name: 'change-password', query: { redirect: to.fullPath } })
        return
    }
    if (to.matched.some(record => record.meta.requiresAdmin) && !store.getters["auth/isAdmin"]) {
        next({ name: 'home' })
        return
    }

    if (to.matched.some(record => record.meta.requiresFleet)) {
        fleetSelected(to, from, next)
    } else {
        next()
    }
})


export default router
