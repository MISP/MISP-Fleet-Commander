import Vue from "vue"
import Vuex from "vuex"
import ui from "./modules/ui"
import settings from "./modules/settings"
import auth from "./modules/auth"
import users from "./modules/users"
import userSettings from "./modules/userSettings"
import servers from "./modules/servers"
import connections from "./modules/connections"
import fleets from "./modules/fleets"
import plugins from "./modules/plugins"
import notifications from "./modules/notifications"
import pinlists from "./modules/pinlists"
import websocket from "./modules/websocket"

Vue.use(Vuex)

// const debug = process.env.NODE_ENV !== 'production'
const debug = false

export default new Vuex.Store({
    modules: {
        ui,
        settings,
        auth,
        users,
        userSettings,
        servers,
        connections,
        fleets,
        notifications,
        pinlists,
        plugins,
        websocket,
    },
    strict: debug,
})
