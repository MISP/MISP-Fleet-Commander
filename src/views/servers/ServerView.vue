<template>
<Layout name="LayoutDefault">
    <div class="page-container">
        <template v-if="isOnline">
            <div class="container-fuild mb-3">
                <div class="row">
                    <div class="col col-md-5 col-xl-4">
                        <ServerViewProfile :server="getServer" @fullRefresh="fullRefresh()"></ServerViewProfile>
                    </div>
                    <div class="col col-md-7 col-xl-8 pl-0">
                        <b-card no-body>
                            <ServerNotifications :server="getServer"></ServerNotifications>
                        </b-card>
                    </div>
                </div>
            </div>

            <div class="container-fuild mb-3">
                <b-card no-body>
                    <serverInfoAndManagements 
                        :server_info="getServer.server_info"
                        :server="getServer"
                        max_content_size="80vh"
                    ></serverInfoAndManagements>
                </b-card>
            </div>
        </template>
        <template v-else>
            <div class="row">
                <div class="col col-md-5 col-xl-4 mx-auto">
                    <ServerViewProfile :server="getServer"></ServerViewProfile>
                </div>
            </div>
        </template>
    </div> 
</Layout>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import Layout from "@/components/layout/Layout.vue"
import ServerViewProfile from "@/views/servers/elements/serverView/serverProfile.vue"
import ServerNotifications from "@/views/servers/elements/serverView/serverNotifications.vue"
import serverInfoAndManagements from "@/views/servers/elements/serverInfoAndManagements.vue"

export default {
    name: "ServerView",
    components: {
        Layout,
        ServerViewProfile,
        ServerNotifications,
        serverInfoAndManagements
    },
    props: {
        server_id: {
            required: true,
            type: Number
        }
    },
    computed: {
        ...mapGetters({
            getServerById: "servers/getServerById"
        }),
        getServer: function() {
            return this.getServerById(this.server_id)
        },
        isOnline: function() {
            return !this.getServer.status.error
        },
    },
    data: function () {
        return {
            statusRefreshInProgress: false,
            infoRefreshInProgress: false,
        }
    },
    methods: {
        getOnlineStatus() {
            return new Promise((resolve, reject) => {
                this.$store.dispatch("servers/refreshAllConnectionState")
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        this.$bvToast.toast(error, {
                            title: "Could not reach Server",
                            variant: "danger",
                        })
                    })
                    .finally(() => {
                        this.statusRefreshInProgress = false
                    })
            })
        },
        fetchServerInfo() {
            this.infoRefreshInProgress = true
            return new Promise((resolve, reject) => {
                this.$store.dispatch("servers/getInfo", {server: this.getServer, no_cache: true})
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        console.log(error)
                        this.$bvToast.toast(error, {
                            title: "Could not fetch server info",
                            variant: "danger",
                        })
                    })
                    .finally(() => {
                        this.infoRefreshInProgress = false
                    })
            })
        },
        fullRefresh() {
            this.getOnlineStatus()
            this.fetchServerInfo()
        }
    },
    mounted() {
        this.fullRefresh()
    }
}
</script>

<style scoped>
.collapsed .when-open,
.not-collapsed .when-closed {
    transform: rotate(180deg);
}

.accordion *:focus {
    outline: 0 !important;
}
</style>
