<template>
    <div class="main">
        <div class="app-header">
            <TheNavBar></TheNavBar>
        </div>
        <div class="app">
            <div class="sidebar">
                <TheSideBar></TheSideBar>
            </div>
            <div :class="['app-body', 'strech', sidebarCollapsed ? 'body-sidebar-collapse' : '']">
                <slot/>
            </div>
        </div>
    </div>
</template>

<script>
// @ is an alias to /src
import { mapState } from "vuex"
import TheSideBar from "@/components/layout/TheSideBar.vue"
import TheNavBar from "@/components/layout/TheNavBar.vue"

export default {
    name: "LayoutDefault",
    components: {
        TheSideBar,
        TheNavBar
    },
    data () {
        return {
            layout: "div"
        }
    },
    computed: {
        ...mapState({
            sidebarCollapsed: state => state.ui.sidebarCollapsed
        }),
    }
}
</script>
