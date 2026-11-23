<template>
    <div id="app">
        <component :is="layout">
            <router-view @update:layout="checkLayout"/>
        </component>

        <TheLoginModal
        ></TheLoginModal>
        <TheSettingsModal
            v-if="isUserAuthed && !mustChangePassword"
        ></TheSettingsModal>
        <JobNotifier
            v-if="isUserAuthed && !mustChangePassword"
        ></JobNotifier>
    </div>
</template>

<script>
import LayoutDefault from "@/components/layout/LayoutDefault.vue"
import LayoutStretch from "@/components/layout/LayoutStretch.vue"
import LayoutLogin from "@/components/layout/LayoutLogin.vue"
import TheLoginModal from '@/views/login/TheLoginModal.vue';
import TheSettingsModal from '@/views/settings/TheSettingsModal.vue';
import JobNotifier from '@/components/jobs/JobNotifier.vue';
import { layoutOf } from "@/helpers/layouts"

export default {
    name: "App",
    components: {
        LayoutDefault,
        LayoutStretch,
        LayoutLogin,
        TheLoginModal,
        TheSettingsModal,
        JobNotifier,
    },
    computed: {
        // From the route (`meta.layout`), known before the page is created: see helpers/layouts.js
        layout() {
            return layoutOf(this.$route)
        },
        isUserAuthed() {
            return this.$store.getters["auth/isAuthenticated"]
        },
        // Nothing else is available until the password is changed: avoid requests bound to fail
        mustChangePassword() {
            return this.$store.getters["auth/mustChangePassword"]
        },
        // The user whose settings apply: set once logged in with a usable account
        settingsUserID() {
            const user = this.$store.getters["auth/user"]
            return this.isUserAuthed && !this.mustChangePassword && user ? user.id : null
        },
    },
    watch: {
        // At start, after logging in (page or popup) and after a required password change
        settingsUserID: {
            handler(userID) {
                if (userID !== null) {
                    this.$store.dispatch('userSettings/getUserSettings').catch(() => {})
                }
            },
            immediate: true,
        },
    },
    methods: {
        // A page still says which layout it is drawn in (<Layout name="…">): the route decides, this only catches a
        // route left without the `meta.layout` its page asks for
        checkLayout(name) {
            if (process.env.NODE_ENV !== "production" && name !== this.layout) {
                console.warn(`The page asks for ${name} but its route gives ${this.layout}: set meta.layout on the route`)
            }
        },
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
    },
}
</script>
