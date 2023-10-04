<template>
    <div id="app">
        <component :is="layout">
            <router-view :layout.sync="layout"/>
        </component>
    </div>
</template>

<script>
import LayoutDefault from "@/components/layout/LayoutDefault.vue"
import LayoutStretch from "@/components/layout/LayoutStretch.vue"
import LayoutLogin from "@/components/layout/LayoutLogin.vue"

export default {
    name: "App",
    components: {
        LayoutDefault,
        LayoutStretch,
        LayoutLogin,
    },
    data () {
        return {
            layout: "div" // fallback value if the layout is not set in the view
        }
    },
    sockets: {
        connect: function () {
            this.$store.commit('websocket/setConnected', true)
            console.log('connect');
        },
        disconnect(reason) {
            this.$store.commit('websocket/setConnected', false)
            console.log('disconnect');
        },
        disconnecting(reason) {
            console.log('disconnecting');
        },
        connect_error(error) {
            console.log('connect_error');
        },
        reconnect() {
        },
    },
}
</script>
