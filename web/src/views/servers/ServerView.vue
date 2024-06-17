<template>
<Layout name="LayoutDefault">
    <div v-if="!getServer" class="d-flex justify-content-center mb-3"><b-spinner label="Loading..."></b-spinner></div>
    <div v-else class="page-container">
        <template v-if="isOnline">
            <div class="container-fuild mb-3">
                <div class="row">
                    <div class="col col-md-5 col-xl-4">
                        <b-overlay :show="server_status_refresh_enqueued[server_id] || server_refresh_enqueued[server_id]" rounded="sm">
                            <ServerViewProfile
                                :server_id="server_id"
                                @wsStatusRefresh="wsStatusRefresh()"
                                @fullRefresh="fullRefresh()"
                            ></ServerViewProfile>
                        </b-overlay>
                    </div>
                    <div class="col col-md-7 col-xl-8 pl-0">
                        <b-overlay :show="server_refresh_enqueued[server_id]" rounded="sm">
                            <b-card no-body>
                                <ServerNotifications :server="getServer"></ServerNotifications>
                            </b-card>
                        </b-overlay>
                    </div>
                </div>
            </div>

            <div class="container-fuild mb-3 server-extra">
                <b-card no-body>
                    <b-overlay :show="server_refresh_enqueued[server_id]" rounded="sm">
                        <serverInfoAndManagements 
                            :server_id="server_id"
                            max_content_size="80vh"
                        ></serverInfoAndManagements>
                    </b-overlay>
                </b-card>
            </div>
        </template>
        <template v-else>
            <div class="row">
                <div class="col col-md-5 col-xl-4 mx-auto">
                    <ServerViewProfile :server_id="server_id"></ServerViewProfile>
                </div>
            </div>
        </template>
    </div> 
</Layout>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import store from "@/store/index"
import Layout from "@/components/layout/Layout.vue"
import { websocketMixin } from "@/helpers/websocketMixin"
import ServerViewProfile from "@/views/servers/elements/serverView/serverProfile.vue"
import ServerNotifications from "@/views/servers/elements/serverView/serverNotifications.vue"
import serverInfoAndManagements from "@/views/servers/elements/serverInfoAndManagements.vue"

export default {
    name: "ServerView",
    mixins: [websocketMixin],
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
        ...mapState({
            servers: state => state.servers.servers,
            server_status: state => state.servers.server_status,
            server_query_in_progress: state => state.servers.server_query_in_progress,
            server_refresh_enqueued: state => state.servers.server_refresh_enqueued,
            server_status_refresh_enqueued: state => state.servers.server_status_refresh_enqueued,
        }),
        getServer: function() {
            return this.servers[this.server_id] || null
        },
        getServerStatus: function() {
            return this.server_status[this.server_id]
        },
        getQueryInProgress: function() {
            return this.server_query_in_progress[this.server_id]
        },
        isOnline: function() {
            return !this.getServerStatus.error
        },
    },
    data: function () {
        return {
            statusRefreshInProgress: false,
        }
    },
    methods: {
        wsStatusRefresh() {
            this.wsServerConnectionTest(this.server_id)
        },
        fullRefresh() {
            this.wsServerConnectionTest(this.server_id)
            this.refreshPluginViewValues()
            this.wsServerRefresh(this.server_id)
        },
        refreshPluginViewValues(no_cache=false) {
            this.$store.dispatch("plugins/fetchViewValues", {no_cache: no_cache, serverID: this.server_id})
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch plugin values",
                        variant: "danger",
                    })
                })
        },
    },
    mounted() {
        this.wsStatusRefresh()
        this.refreshPluginViewValues()
        this.$store.dispatch("plugins/getPlugins", {use_cache: true})
    },
    beforeRouteEnter(to, from, next) {
        if (store.getters["fleets/selectedFleet"] === null) {
            store.dispatch("fleets/selectFleetFromServerId", to.params.server_id).then(() => {
                store.dispatch("servers/fetchServers", {force: true})
                next()
            }).catch(() => {
                next("/home")
            })
        } else {
            next()
        }
    },
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

.server-extra {
    min-height: 500px;
}
</style>
