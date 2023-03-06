<template>
    <b-tabs @input="handleTabChange" ref="tabs" card>
        <b-tab class="p-1" no-body lazy>
            <template #title>
                <i class="fas fa-tools mr-1"></i><strong>Remote administration</strong>
            </template>
            <div :style="getMaxHeight">
                <keep-alive>
                <MISPRemoteAdministration
                    :server_id="server_id"
                ></MISPRemoteAdministration>
                </keep-alive>
            </div>
        </b-tab>
        <b-tab class="p-1" no-body lazy>
            <template #title>
                <i class="fas fa-plug mr-1"></i><strong>Plugins</strong>
            </template>
            <div :style="getMaxHeight">
                <keep-alive>
                    <pluginAction
                        :server_id="server_id"
                    ></pluginAction>
                </keep-alive>
            </div>
        </b-tab>
        <b-tab title="Diagnostic" class="p-1" active no-body lazy>
            <keep-alive>
            <b-card no-body>
                <b-tabs pills card vertical>
                    <b-tab
                        v-for="(value, setting) in getDiagnostic"
                        v-bind:key="setting"
                        :title="setting"
                        lazy
                    >
                        <b-card-text>
                            <div :style="getMaxHeight">
                                <MISPSchemaDiagnostic
                                    v-if="setting == 'dbSchemaDiagnostics'"
                                    :schemaDiagnostic="value"
                                ></MISPSchemaDiagnostic>
                                <b-table
                                    v-else-if="isTabularView(setting)"
                                    striped
                                    table-class="table-no-select"
                                    :fields="fieldsFromObject(value[0])"
                                    :items="value"
                                ></b-table>
                                <b-table-simple
                                    v-else-if="isListView(setting)"
                                    striped small
                                    class="mb-0"
                                    :bordered="false"
                                    :borderless="true"
                                    :outlined="false"
                                >
                                    <b-tbody>
                                        <b-tr v-for="(v, k) in value" v-bind:key="k">
                                            <b-th>{{ k }}</b-th>
                                            <b-td v-if="isJson(v)">
                                                <jsonViewer
                                                    :item="v"
                                                    :open="true"
                                                ></jsonViewer>
                                            </b-td>
                                            <b-td v-else>{{ v }}</b-td>
                                        </b-tr>
                                    </b-tbody>
                                </b-table-simple>
                                <jsonViewer
                                    v-else
                                    :item="value"
                                    :rootKeyName="setting"
                                    :open="true"
                                ></jsonViewer>
                            </div>
                        </b-card-text>
                    </b-tab>
                </b-tabs>
            </b-card>
            </keep-alive>
        </b-tab>
        <b-tab title="Usage" no-body lazy>
            <keep-alive>
            <b-card no-body>
                <div :style="getMaxHeight">
                    <b-table-simple
                        striped small
                        class="mb-0"
                        :bordered="false"
                        :borderless="true"
                        :outlined="false"
                    >
                        <b-tbody>
                            <b-tr v-for="(v, k) in getServerUsage.stats" v-bind:key="k">
                                <b-th>{{ k }}</b-th>
                                <b-td>{{ v }}</b-td>
                            </b-tr>
                        </b-tbody>
                    </b-table-simple>
                </div>
            </b-card>
            </keep-alive>
        </b-tab>
        <b-tab title="User profile" class="p-1" no-body lazy>
            <keep-alive>
            <b-card no-body>
                <div :style="getMaxHeight">
                    <jsonViewer
                        :item="getServerUser"
                        rootKeyName="User profile"
                        :open="true"
                    ></jsonViewer>
                </div>
            </b-card>
            </keep-alive>
        </b-tab>
        <b-tab title="Connected MISP servers" class="p-1" no-body lazy>
            <keep-alive>
            <b-card class="border-0" no-body>
                <div class="p-2" :style="getMaxHeight">
                    <MISPConnectedServers
                        :servers="getRemoteConnections"
                    ></MISPConnectedServers>
                </div>
            </b-card>
            </keep-alive>
        </b-tab>
        <b-tab title="Content" class="p-1" no-body disabled lazy>
            <b-card no-body>
                Content
            </b-card>
        </b-tab>

        <template v-slot:tabs-end>
            <b-nav-item href="#" class="ml-auto rightmost-action" link-classes="no-pointer">
                <timeSinceRefresh
                    :timestamp="getLastRefresh"
                    type="ddd DD/MM/YYYY HH:mm"
                ></timeSinceRefresh>
                <template v-if="inServerIndex">
                    <b-button variant="primary" size="sm" @click="refreshDiagnostic()">
                        <iconButton
                            text="Refresh"
                            icon="sync-alt"
                            :tight="true"
                        ></iconButton>
                    </b-button>
                    <b-button class="ml-1 darken-on-hover" size="xs" variant="link" @click="closeDetails()">
                        <i class="fas fa-times"></i>
                    </b-button>
                </template>
            </b-nav-item>
        </template>
    </b-tabs>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import iconButton from "@/components/ui/elements/iconButton.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"
import MISPRemoteAdministration from "@/views/servers/elements/MISPRemoteAdministration.vue"
import MISPSchemaDiagnostic from "@/views/servers/elements/MISPSchemaDiagnostic.vue"
import MISPConnectedServers from "@/views/servers/elements/MISPConnectedServers.vue"
import pluginAction from "@/views/servers/elements/pluginAction.vue"

export default {
    name: "serverInfoAndManagements",
    components: {
        timeSinceRefresh,
        jsonViewer,
        iconButton,
        MISPRemoteAdministration,
        MISPSchemaDiagnostic,
        MISPConnectedServers,
        pluginAction,
    },
    props: {
        server_id: {
            required: true,
            type: Number,
        },
        max_content_size: {
            type: String,
            default: "700px"
        }
    },
    data: function() {
        return {
            diagnosticTabularView: [],
            diagnosticListView: ["dbDiagnostics", "dbSchemaDiagnostic", "moduleStatus", "readableFiles", "redisInfo", "version", "writeableDirs", "writeableFiles"],
            initDone: false,
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
            server_status: state => state.servers.server_status,
            server_query_in_progress: state => state.servers.server_query_in_progress,
            remote_connections: state => state.servers.remote_connections,
            server_usage: state => state.servers.server_usage,
            server_user: state => state.servers.server_user,
            server_users: state => state.servers.server_users,
            final_settings: state => state.servers.final_settings,
            last_refresh: state => state.servers.last_refresh,
            diagnostic_full: state => state.servers.diagnostic_full,
        }),
        getServer: function() {
            return this.servers[this.server_id]
        },
        getRemoteConnections: function() {
            return this.remote_connections[this.server_id]
        },
        getQueryInProgress: function() {
            return this.server_query_in_progress[this.server_id]
        },
        getDiagnostic() {
            const diagnostic = Object.assign({}, this.diagnostic_full[this.server_id])
            delete diagnostic._latency
            return diagnostic
        },
        getServerUsage: function() {
            return this.server_usage[this.server_id]
        },
        getServerUser: function() {
            return this.server_user[this.server_id]
        },
        getServerUsers: function() {
            return this.server_users[this.server_id]
        },
        getLastRefresh: function() {
            return this.last_refresh[this.server_id]
        },
        inServerIndex() {
            return this.$route.name === "servers.index"
        },
        getMaxHeight() {
            return {
                "max-height": this.max_content_size,
                "overflow-y": "auto",
            }
        }
    },
    methods: {
        refreshDiagnostic() {
            this.$emit("actionRefresh", "no_cache")
        },
        closeDetails() {
            this.$emit("actionClose", "no_cache")
        },
        isTabularView(name) {
            return this.diagnosticTabularView.includes(name)
        },
        isListView(name) {
            return this.diagnosticListView.includes(name)
        },
        fieldsFromObject(object) {
            return Object.keys(object).map(key => {
                return {
                    key: key,
                    sortable: true
                }
            })
        },
        isJson(value) {
            return typeof value === "object"
        },
        handleTabChange(tabIndex) {
            if (this.initDone) {
                this.$nextTick(function () {
                    const el = this.$refs.tabs.tabs[tabIndex].$el
                    el.scrollIntoView(true)
                })
            } else {
                this.initDone = true
            }
        }
    }
}
</script>

<style scoped>
ul.nav-tabs > li.nav-item.rightmost-action > a {
    padding-bottom: 0;
    margin-top: -10px;
    margin-right: -15px;
}

ul.nav-tabs > li.nav-item.rightmost-action > a:hover {
    border: 1px solid #ffffff00;
}
ul.nav-tabs > li.nav-item.rightmost-action > a:focus {
    border: 1px solid #ffffff00;
}

ul.nav-tabs > li.nav-item.rightmost-action > a.no-pointer {
    cursor: auto;
}

.darken-on-hover > i.fas{
    color: #6c757d;
}
.darken-on-hover:hover > i.fas{
    color: #5a6268;
}
</style>
