import Vue from "vue"
import Vuex from "vuex"
import ui from "./modules/ui"
import servers from "./modules/servers"
import connections from "./modules/connections"

Vue.use(Vuex)

const debug = "production"

export default new Vuex.Store({
    modules: {
        ui,
        servers,
        connections
    },
    strict: debug,
})