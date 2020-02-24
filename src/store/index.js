import Vue from "vue"
import Vuex from "vuex"
import ui from "./modules/ui"
import servers from "./modules/servers"

Vue.use(Vuex)

const debug = "production"

export default new Vuex.Store({
    modules: {
        ui,
        servers,
    },
    strict: debug,
})