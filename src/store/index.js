import Vue from "vue"
import Vuex from "vuex"
import ui from "./modules/ui"
import config from "./modules/config"
import servers from "./modules/servers"
import connections from "./modules/connections"
import serverGroups from "./modules/serverGroups"
import notifications from "./modules/notifications"

Vue.use(Vuex)

//const debug = process.env.NODE_ENV !== 'production'
const debug = false

export default new Vuex.Store({
    modules: {
        ui,
        config,
        servers,
        connections,
        serverGroups,
        notifications,
    },
    strict: debug,
})
