<template>
    <div class="main">
        <!-- <div class="app">
            <div class="sidebar">
                <TheSideBar></TheSideBar>
            </div>
            <div class="app-body container-fluid body-sidebar-collapse pl-0">
                <slot/>
            </div>
        </div> -->
        <div class="d-flex">
            <div class="sidebar">
                <TheSideBar></TheSideBar>
            </div>
            <div class="d-flex flex-column flex-fill main-body">
                <TheNavBar></TheNavBar>
                <div class="container-fuild p-3 pb-0 mt-5">
                    <slot/>
                </div>
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
        TheNavBar,
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
