<template>
    <div class="main">
        <div class="app">
            <div class="sidebar">
                <TheSideBar></TheSideBar>
            </div>
            <div class="d-flex flex-column flex-fill main-body">
                <TheNavBar></TheNavBar>
                <div class="layout-stretch">
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
    name: "LayoutStretch",
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
    }
}
</script>
