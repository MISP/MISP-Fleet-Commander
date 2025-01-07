<template>
    <div>
        
        <b-card no-body
            v-show="(hasSelection || true)"
            bg-variant=""
            text-variant=""
            id="networkNodeInfoPanel"
            style="box-shadow: rgba(0, 0, 0, 0.07) 0px 1px 1px, rgba(0, 0, 0, 0.07) 0px 2px 2px, rgba(0, 0, 0, 0.07) 0px 4px 4px, rgba(0, 0, 0, 0.07) 0px 8px 8px, rgba(0, 0, 0, 0.07) 0px 16px 16px;"
        >
            <b-card-title class="px-2 pt-1 mb-0" style="background-color: rgba(0, 0, 0, 0.03);">
                <h5 id="sidebar-no-header-title" class="mb-0 d-flex">
                    <span>{{ getServer.name }}</span>
                    <span style="font-size: 0.66em;" class="ml-auto">
                        <timeSinceRefresh :timestamp="lastRefreshTimestamp" :clockNoMargin="true"></timeSinceRefresh>
                        <b-button
                            variant="primary"
                            class="ml-auto"
                            size="sm"
                            title="Quick refresh"
                            @click="wsStatusRefresh()"
                        >
                            <i class="fas fa-redo-alt"></i>
                        </b-button>
                    </span>
                </h5>
                <div class="font-weight-light mb-2" style="font-size: 0.6em;">
                    {{ getServer.url }}
                </div>
            </b-card-title>
            <b-tabs
                card fill pills
                nav-wrapper-class="px-3 py-1"
            >
                <b-tab title="Info" no-body active>
                    <b-table
                        striped small
                        class="mb-0"
                        :bordered="false"
                        :borderless="true"
                        :outlined="false"
                        :items="serverInfoTable"
                        :fields="fields"
                    >
                    </b-table>
                </b-tab>
                <b-tab title="Diagnostic">
                    Diagnostic
                </b-tab>
                <b-tab title="Content">
                    Event pic and data
                </b-tab>
            </b-tabs>

        </b-card>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import { websocketMixin } from "@/helpers/websocketMixin"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"

export default {
    name: "TheNodeInfoCard",
    mixins: [websocketMixin],
    components: {
        timeSinceRefresh
    },
    props: {
        server_id: {
            type: Number,
            required: true
        },
    },
    data: function() {
        return {
            fields: [
                { key: "property", thStyle: { display: "none" } },
                { key: "value", thStyle: { display: "none" } }
            ]
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
            connections: state => state.connections.all,
            server_status: state => state.servers.server_status,
            server_usage: state => state.servers.server_usage,
            server_user: state => state.servers.server_user,
            remote_connections: state => state.servers.remote_connections,
        }),
        getServer: function() {
            return this.servers[this.server_id] || null
        },
        getServerStatus: function() {
            return this.server_status[this.server_id] || null
        },
        getServerUsage: function() {
            return this.server_usage[this.server_id] || null
        },
        getQueryInProgress: function() {
            return this.server_query_in_progress[this.server_id] || null
        },
        getServerUser: function() {
            return this.server_user[this.server_id] || null
        },
        isOnline: function() {
            return !this.getServerStatus.error
        },
        lastRefreshTimestamp: function() {
            return this.getServer?.server_info?.timestamp || null
        },
        hasSelection() {
            return Object.keys(this.getServer).length > 0
        },
        serverInfoTable() {
            let items = []
            if (!this.getServer) {
                return items
            }
            items = items.concat([
                {
                    property: "Name",
                    value: this.getServer.name
                },
                {
                    property: "URL",
                    value: this.getServer.url
                },
            ])
            if (
                this.getServer.server_info !== undefined &&
                this.getServerUser.Organisation !== undefined
            ) {
                items = items.concat([
                    {
                        property: "Org. name",
                        value: this.getServerUser.Organisation.name
                    },
                    {
                        property: "Org. uuid",
                        value: this.getServerUser.Organisation.uuid
                    },
                    {
                        property: "Org. type",
                        value: this.getServerUser.Organisation.type
                    }
                ])
            } else {
                items = items.concat([
                    {
                        property: "Org. name",
                        value: ""
                    },
                    {
                        property: "Org. uuid",
                        value: ""
                    },
                    {
                        property: "Org. type",
                        value: ""
                    }
                ])
            }
            return items
        },
    },
    methods: {
        wsStatusRefresh() {
            this.wsServerRefresh(this.server_id)
        },
    }
}
</script>

<style scoped>
    .close-button {
        right: 4px;
        top: 0;
        user-select: none;
    }
</style>

<style>
    .right-panel {
        z-index: 2;
    }

    .right-panel .card-header {
        padding: 0.5rem 0.5rem;
        cursor: move;
    }
    
    .right-panel .card-header > ul.card-header-tabs {
        margin-left: 0;
        margin-right: 0;
        margin-bottom: -0.5rem;
    }
    
    .right-panel .card-header > ul.card-header-tabs > li.nav-item {
    
    }
    
    .right-panel .card-header > ul.card-header-tabs > li.nav-item > a.nav-link {
        padding: 0.3rem 0;
        user-select: none;
    }
    
    .right-panel .card-footer {
        padding: 0.2rem 1rem;
    }

    .right-panel table {
        /* font-size: 0.7rem; */
    }
</style>