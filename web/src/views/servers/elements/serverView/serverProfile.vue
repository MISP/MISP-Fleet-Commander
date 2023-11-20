<template>
    <b-card no-body>
        <b-card-body class="d-flex flex-column align-items-center p-3">
                <h4 class="mb-0">{{ getServer.name }}</h4>
            <b-link :href="getServer.url" target="_blank" class="text-nowrap mb-2">
                {{ getServer.url }}
                <sup class="fa fa-external-link-alt"></sup>
            </b-link>
            <b-img fuild :src="welcomePicture" :alt="getServer.name" class="mb-2" height="150" width="200"></b-img>
            <span class="text-muted">{{ getServer.comment }}</span>
        </b-card-body>
        <hr class="my-0" />
        <b-card-body class="px-3 py-2" role="tab">
            <h5 class="mb-2 d-flex ">
                Server Status
                <span class="ml-auto">
                    <span :class="['text-nowrap', 'my-auto', 'h6', {'text-danger': getServerStatus.error, 'text-success': !getServerStatus.error}]">
                        <b-icon v-if="getServerStatus.data !== undefined" icon="circle-fill" class=""></b-icon>
                        {{ serverStatusText }}
                        <small
                             v-if="getServerStatus.latency !== undefined"
                             :class="{'text-success': getServerStatus.latency < 0.3, 'text-warning': getServerStatus.latency >= 0.3 && getServerStatus.latency < 2, 'text-danger': getServerStatus.latency >= 2}"
                        >
                            ({{ (getServerStatus.latency*1000).toFixed(0) }}ms)
                        </small>
                    </span>
                    <b-button
                        class="ml-auto mr-1 p-0"
                        variant="link"
                        size="sm"
                        title="Inline full refresh"
                        @click="fullRefresh()"
                    >
                        <i class="fas fa-sync-alt"></i>
                    </b-button>
                    <b-button
                        :variant="getRefreshEnqueued ? 'dark' : 'primary'"
                        :disabled="getRefreshEnqueued"
                        size="sm"
                        title="Enqueue full refresh"
                        href="#"
                        @click="wsRefresh()"
                    >
                        <span v-if="getRefreshEnqueued">
                            <i class="fas fa-sync-alt fa-spin"></i>
                            Refresh in progress
                        </span>
                        <span v-else>
                            <i class="fas fa-clock"></i>
                            Enqueue refresh
                        </span>
                    </b-button>
                </span>
            </h5>

            <b-overlay :show="getQueryInProgress" rounded="sm">
                <template v-if="isOnline">
                    <b-table-simple
                    small
                    class="mb-0"
                    :bordered="false"
                    :borderless="true"
                    :outlined="false"
                    >
                        <b-tbody>
                            <b-tr v-for="(v, k) in statusData" v-bind:key="k">
                                <b-th class="text-nowrap text-right pr-3">{{ k }}</b-th>
                                <b-td>
                                    <template v-if="v.text">
                                        {{ v.text }}
                                    </template>
                                    <template v-if="v.component">
                                        <component :is="v.component" v-bind="v.data"></component>
                                    </template>
                                </b-td>
                            </b-tr>
                        </b-tbody>
                    </b-table-simple>
                </template>
            </b-overlay>
        </b-card-body>
        <hr v-if="isOnline" class="my-0" />

        <b-card-body v-if="isOnline" class="p-0" role="tab">
            <h5 class="card-title mb-0 mx-3 my-2">
                Server Info
            </h5>
            <b-overlay :show="getQueryInProgress" rounded="sm" class="table-server-info">
                <b-table-simple
                striped small
                class="mb-0"
                :bordered="false"
                :borderless="true"
                :outlined="false"
                >
                    <b-tbody>
                        <b-tr v-for="(v, k) in infoData" v-bind:key="k">
                            <b-th class="text-nowrap text-right pr-3">{{ k }}</b-th>
                            <b-td>
                                <template v-if="Object.keys(defaultInfoData).includes(k)">{{ v }}</template>
                                <template v-else>
                                    <pluginValueRenderer
                                        v-if="v !== undefined"
                                        :server_id="server_id"
                                        :plugin_name="k" 
                                        :plugin_response="v" 
                                    ></pluginValueRenderer>
                                </template>
                            </b-td>
                        </b-tr>
                    </b-tbody>
                </b-table-simple>
            </b-overlay>
        </b-card-body>
    </b-card>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import userPerms from "@/views/servers/elements/userPerms.vue"
import proxyStatus from "@/views/servers/elements/proxyStatus.vue"
import workersStatus from "@/views/servers/elements/workersStatus.vue"
import submodulesStatus from "@/views/servers/elements/submodulesStatus.vue"
import zeroMQStatus from "@/views/servers/elements/zeroMQStatus.vue"
import connectionsSummary from "@/views/servers/elements/connectionsSummary.vue"
import pluginValueRenderer from "@/views/servers/elements/pluginValueRenderer.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"

export default {
    name: "ServerViewProfile",
    components: {
        pluginValueRenderer,
    },
    props: {
        server_id: {
            required: true,
            type: Number,
        },
        // info_refresh_in_progress: {
        //     required: true,
        //     type: Boolean,
        // }
    },
    data: function () {
        return {
            defaultInfoData: {
                "MISP UUID": "",
            }
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
            server_status: state => state.servers.server_status,
            server_query_in_progress: state => state.servers.server_query_in_progress,
            server_query_error: state => state.servers.server_query_error,
            server_refresh_enqueued: state => state.servers.server_refresh_enqueued,
            server_user: state => state.servers.server_user,
            remote_connections: state => state.servers.remote_connections,
            submodules: state => state.servers.submodules,
            proxy: state => state.servers.proxy,
            zeromq: state => state.servers.zeromq,
            workers: state => state.servers.workers,
            server_users: state => state.servers.server_users,
            last_refresh: state => state.servers.last_refresh,
            final_settings: state => state.servers.final_settings,
            allPluginValues: state => state.plugins.pluginViewValues,
        }),
        ...mapGetters({
            viewPlugins: "plugins/viewPlugins",
        }),
        pluginValuesForServer: function() {
            return this.allPluginValues[this.server_id]
        },
        getServer: function() {
            return this.servers[this.server_id]
        },
        getQueryInProgress: function() {
            return this.server_query_in_progress[this.server_id]
        },
        getRefreshEnqueued: function() {
            return this.server_refresh_enqueued[this.server_id]
        },
        getServerStatus: function() {
            return this.server_status[this.server_id]
        },
        getFinalSettings: function() {
            return this.final_settings[this.server_id]
        },
        getProxy: function() {
            return this.proxy[this.server_id]
        },
        getWorkers: function() {
            return this.workers[this.server_id]
        },
        getRemoteConnections: function() {
            return this.remote_connections[this.server_id]
        },
        getSubmodules: function() {
            return this.submodules[this.server_id]
        },
        getZmq: function() {
            return this.zeromq[this.server_id]
        },
        getServerUser: function() {
            return this.server_user[this.server_id]
        },
        isOnline: function() {
            return !this.getServerStatus.error
        },
        serverStatusText: function() {
            return this.isOnline ? "Online" : "Offline"
        },
        welcomePicture: function() {
            return this.MISPMainLogo ? `${this.getServer.url}/img/custom/${this.MISPMainLogo}` : `${this.getServer.url}/img/misp-logo.png`
        },
        MISPMainLogo: function() {
            return this.getFinalSettings['MISP.main_logo']
        },
        statusData: function() {
            let status = {
                "Last refresh": {
                    data: {
                        timestamp: this.last_refresh[this.server_id],
                        type: "ddd DD/MM/YYYY HH:mm",
                    },
                    component: timeSinceRefresh,
                },
                "Connection Test": {
                    text: this.getServerStatus.data,
                },
                "Proxy": {
                    data: {
                        proxy: this.getProxy,
                    },
                    component: proxyStatus,
                },
                "Workers": {
                    data: {
                        workers: this.getWorkers,
                        server_id: this.server_id,
                    },
                    component: workersStatus,
                },
                "Remote Connections": {
                    data: {
                        connections: this.getRemoteConnections,
                        row_index: 0,
                    },
                    component: connectionsSummary,
                },
                "User permissions": {
                    data: {
                        perms: this.getServerUser['Role'],
                        row_id: 0,
                        context: "serverView"
                    },
                    component: userPerms,
                },
                "Sub-modules": {
                    data: {
                        submodules: this.getSubmodules,
                    },
                    component: submodulesStatus,
                },
                "ZeroMQ": {
                    data: {
                        status: this.getZmq,
                        server_id: this.server_id,
                    },
                    component: zeroMQStatus,
                },
            }
            return status
        },
        infoData: function() {
            let info = Object.assign({}, this.defaultInfoData)
            if (this.getFinalSettings.error !== undefined) {
                return info
            }
            info["MISP UUID"] = this.getFinalSettings['MISP.uuid']
            this.viewPlugins.forEach(plugin => {
                info[plugin.name] = this.pluginValuesForServer ? (this.pluginValuesForServer[plugin.id] || {}) : {}
            })
            return info
        }
    },
    methods: {
        fullRefresh() {
            this.$emit("fullRefresh")
        },
        wsRefresh() {
            this.$emit("wsRefresh")
        }
    }
}
</script>

<style scoped>
    .table-server-info {
        max-height: 20rem;
        overflow: auto;
    }
</style>
