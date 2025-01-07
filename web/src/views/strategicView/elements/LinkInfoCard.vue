<template>
    <div>
        <b-card no-body
            v-show="(hasSelection || true)"
            bg-variant=""
            text-variant=""
            id="networkLinkInfoPanel"
            style="box-shadow: rgba(0, 0, 0, 0.07) 0px 1px 1px, rgba(0, 0, 0, 0.07) 0px 2px 2px, rgba(0, 0, 0, 0.07) 0px 4px 4px, rgba(0, 0, 0, 0.07) 0px 8px 8px, rgba(0, 0, 0, 0.07) 0px 16px 16px;"
        >
            <b-tabs
                card fill pills
                nav-wrapper-class="px-3 py-1"
            >
                <b-tab title="Connection Info" active no-body>
                    <div class="d-flex flex-column align-items-center mx-2 my-3">
                        <h6 class="mb-0">{{ getSourceServer.name }}</h6>
                        <a
                            :href="getSourceServer.url"
                            target="_blank"
                            class="text-muted font-weight-light text-wrap"
                            style="font-size: 0.8em;"
                        >
                            {{ getSourceServer.url }}
                            <sup class="fa fa-external-link-alt text-muted"></sup>
                        </a>
                        <i class="fa fa-arrow-down my-1" style="font-size: 1.5em;"
                            :style="{color: !connectionHasRules ? '#2ca1db' : '#f5854d', filter: !connectionHasRules ? 'drop-shadow(0px 1px 1px rgba(0, 0, 0, .7))' : 'drop-shadow(0px 1px 1px #5b4a4299)'}"
                        ></i>
                        <h6 class="mb-0">{{ getTargetServer.name }}</h6>
                        <a
                            :href="getTargetServer.url"
                            target="_blank"
                            class="text-muted font-weight-light text-wrap"
                            style="font-size: 0.8em;"
                        >
                            {{ getTargetServer.url }}
                            <sup class="fa fa-external-link-alt text-muted"></sup>
                        </a>
                    </div>

                    <b-table-simple striped small class="mb-0">
                        <b-tbody>
                            <b-tr>
                                <b-th>Status</b-th>
                                <b-td>
                                    <connectionStatus
                                        :connection="getConnection"
                                    ></connectionStatus>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>Local Version</b-th>
                                <b-td>
                                    <ConnectionLocalVersion
                                        :connection="getConnection"
                                    ></ConnectionLocalVersion>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>Remote Version</b-th>
                                <b-td>
                                    <ConnectionRemoteVersion
                                        :connection="getConnection"
                                    ></ConnectionRemoteVersion>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>Compatibility</b-th>
                                <b-td>
                                    <ConnectionCompatibility
                                        :connection="getConnection"
                                    ></ConnectionCompatibility>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>POST Test</b-th>
                                <b-td>
                                    <ConnectionPostTest
                                        :connection="getConnection"
                                    ></ConnectionPostTest>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>User</b-th>
                                <b-td>
                                    <ConnectionUser
                                        :connection="getConnection"
                                    ></ConnectionUser>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>User Role</b-th>
                                <b-td>
                                    <ConnectionUserRole
                                        :connection="getConnection"
                                    ></ConnectionUserRole>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>User Sync Flag</b-th>
                                <b-td>
                                    <ConnectionSyncStatus
                                        :connection="getConnection"
                                    ></ConnectionSyncStatus>
                                </b-td>
                            </b-tr>
                        </b-tbody>
                    </b-table-simple>

                </b-tab>
                <b-tab title="Rules" no-body>
                    <template #title>
                        Rules <b-badge :variant="connectionHasRules ? 'primary' : 'secondary'">{{ connectionRuleNumber }}</b-badge>
                    </template>
                    
                    <ConnectionRules
                        :connection="getConnection"
                    ></ConnectionRules>
                </b-tab>
            </b-tabs>

        </b-card>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import connectionStatus from "@/views/servers/elements/connectionStates/connectionStatus.vue"
import ConnectionLocalVersion from "@/views/servers/elements/connectionStates/connectionLocalVersion.vue";
import ConnectionRemoteVersion from "@/views/servers/elements/connectionStates/connectionRemoteVersion.vue";
import ConnectionSyncStatus from "@/views/servers/elements/connectionStates/connectionSyncStatus.vue";
import ConnectionUser from "@/views/servers/elements/connectionStates/connectionUser.vue";
import ConnectionUserRole from "@/views/servers/elements/connectionStates/connectionUserRole.vue";
import ConnectionCompatibility from "@/views/servers/elements/connectionStates/connectionCompatibility.vue";
import ConnectionPostTest from "@/views/servers/elements/connectionStates/connectionPostTest.vue";
import ConnectionRules from "@/views/strategicView/elements/ConnectionRules.vue";

export default {
    name: "TheLinkInfoCard",
    components: {
        timeSinceRefresh,
        connectionStatus,
        ConnectionLocalVersion,
        ConnectionRemoteVersion,
        ConnectionSyncStatus,
        ConnectionUser,
        ConnectionUserRole,
        ConnectionCompatibility,
        ConnectionPostTest,
        ConnectionRules,
    },
    props: {
        link_id: {
            type: String,
            required: true
        },
        link: {
            type: Object,
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
        getConnection: function() {
            return this.connections.filter((connection) => {
                return connection.vid == this.link_id
            })[0] || null
        },
        getSourceServer: function() {
            return this.getConnection.source || null
        },
        getTargetServer: function() {
            return this.link.target || null
        },
        getServerUser: function() {
            return this.server_user[this.server_id] || null
        },
        connectionHasRules: function() {
            return this.connectionRuleNumber > 0
        },
        connectionRuleNumber: function() {
            return !this.getConnection.filtering_rules ? 0 : this.getConnection.filtering_rules.pull_rule_number + this.getConnection.filtering_rules.push_rule_number
        },
        isOnline: function() {
            return !this.getServerStatus.error
        },
        hasSelection() {
            return false
        },
        serverInfoTable() {
            return []
        },
    },
    methods: {
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
