<template>
    <div class="main">
        <div class="d-flex">
            <div class="sidebar">
                <TheSideBar></TheSideBar>
            </div>
            <div class="d-flex flex-column flex-fill main-body">
                <TheNavBar></TheNavBar>
                <div class="container-fuild px-3 pb-0 pt-4 mt-5">
                    <div class="important-alerts">
                        <b-alert variant="danger" :show="worker_health_status === false">
                            <strong><i class="fa fa-triangle-exclamation"></i> Warning:</strong>
                            The background workers are either stuck or not running.
                        </b-alert>
                    </div>
                    <slot/>
                </div>
            </div>
        </div>
        <b-modal id="reauthentication-modal">Hello From My Modal!</b-modal>
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
            worker_health_status: state => state.ui.worker_health_status,
        }),
    },
}
</script>
