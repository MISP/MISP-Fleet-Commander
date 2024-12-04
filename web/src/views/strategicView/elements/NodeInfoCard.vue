<template>
    <b-card no-body
        v-show="open && (hasSelection || true)"
        bg-variant=""
        text-variant=""
        id="networkNodeInfoPanel"
    >
        <b-tabs
            card fill small
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
            <template v-slot:tabs-end>
                <b-btn-close
                    class="position-absolute close-button"
                    @click.prevent="close"
                ></b-btn-close>
            </template>
        </b-tabs>

        <template v-slot:footer>
            <timeSinceRefresh
                v-if="getServer && getServer.status"
                :key="getServer.id"
                :timestamp="getServerStatus.timestamp"
            ></timeSinceRefresh>
            <!-- <timeSinceRefresh
                :timestamp="server.server_info.query_result.timestamp"
            ></timeSinceRefresh> -->
        </template>
    </b-card>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"

export default {
    name: "TheNodeInfoCard",
    components: {
        timeSinceRefresh
    },
    props: {
        server_id: {
            type: Number,
            required: true
        },
        open: {
            type: Boolean,
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
                {
                    property: "Auth key",
                    value: this.getServer.authkey
                }
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
        close() {
            this.$emit("update:open", false)
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
        font-size: 0.7rem;
    }
</style>