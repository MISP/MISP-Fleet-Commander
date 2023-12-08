<template>
    <div id="app">
        <component :is="layout">
            <router-view :layout.sync="layout"/>
        </component>

        <TheLoginModal
        ></TheLoginModal>
    </div>
</template>

<script>
import LayoutDefault from "@/components/layout/LayoutDefault.vue"
import LayoutStretch from "@/components/layout/LayoutStretch.vue"
import LayoutLogin from "@/components/layout/LayoutLogin.vue"
import TheLoginModal from '@/views/login/TheLoginModal.vue';

export default {
    name: "App",
    components: {
        LayoutDefault,
        LayoutStretch,
        LayoutLogin,
        TheLoginModal,
    },
    data () {
        return {
            layout: "div" // fallback value if the layout is not set in the view
        }
    },
    sockets: {
        connect: function () {
            this.$store.commit('websocket/setConnected', true)
            console.debug('connect');
        },
        disconnect(reason) {
            this.$store.commit('websocket/setConnected', false)
            console.debug('disconnect');
        },
        disconnecting(reason) {
            console.debug('disconnecting');
        },
        connect_error(error) {
            console.debug('connect_error');
        },
        reconnect() {
        },
    }
}
</script>
