<template>
    <div class="main">
        <div class="app">
            <div class="sidebar">
                <TheSideBar></TheSideBar>
            </div>
            <div class="app-body container-fluid body-sidebar-collapse pl-0">
                <slot/>
            </div>
        </div>
    </div>
</template>

<script>
// @ is an alias to /src
import { mapState } from "vuex"
import TheSideBar from "@/components/layout/TheSideBar.vue"

export default {
    name: "LayoutDefault",
    components: {
        TheSideBar,
    },
    data () {
        return {
            layout: "div"
        }
    },
    computed: {
        ...mapState({
        }),
    },
}
</script>
