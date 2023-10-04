import Vue from "vue"
import Vuex from "vuex"
import ui from "./modules/ui"
import config from "./modules/config"
import auth from "./modules/auth"
import users from "./modules/users"
import servers from "./modules/servers"
import connections from "./modules/connections"
import serverGroups from "./modules/serverGroups"
import plugins from "./modules/plugins"
import notifications from "./modules/notifications"
import websocket from "./modules/websocket"

Vue.use(Vuex)

// const debug = process.env.NODE_ENV !== 'production'
const debug = false

export default new Vuex.Store({
    modules: {
        ui,
        config,
        auth,
        users,
        servers,
        connections,
        serverGroups,
        notifications,
        plugins,
        websocket,
    },
    strict: debug,
})
