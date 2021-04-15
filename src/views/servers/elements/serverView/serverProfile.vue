<template>
    <b-card no-body>
        <b-card-body class="d-flex flex-column align-items-center p-3">
                <h4 class="mb-0">{{ server.name }}</h4>
            <b-link :href="server.name" target="_blank" class="text-nowrap mb-2">
                {{ server.url }}
                <sup class="fa fa-external-link-alt"></sup>
            </b-link>
            <b-img fuild src="https://iglocska.eu/img/misp-logo.png" :alt="server.name" class="mb-2" height="150"></b-img>
            <span class="text-muted">{{ server.comment }}</span>
        </b-card-body>
            <hr class="my-0" />
            <b-card-body class="px-3 py-2" role="tab">
                <h5 class="mb-2 d-flex ">
                    Server Status
                    <span :class="['text-nowrap', 'ml-auto', 'h6', {'text-danger': server.status.error, 'text-success': !server.status.error}]">
                        <b-icon v-if="server.status.data !== undefined" icon="circle-fill" class=""></b-icon>
                        {{ serverStatusText }}
                    </span>
                </h5>
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
            </b-card-body>
            <hr class="my-0" />

            <b-card-body class="p-0 pb-2" role="tab">
                <h5 class="card-title mb-0 mx-3 my-2">
                    Server Info
                </h5>
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
                            <b-td>{{ v }}</b-td>
                        </b-tr>
                    </b-tbody>
                </b-table-simple>
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

export default {
    name: "ServerViewProfile",
    components: {
    },
    props: {
        server: {
            required: true,
            type: Object
        }
    },
    computed: {
        serverStatusText: function() {
            return !this.server.status.error ? "Online" : "Offline"
        },
        statusData: function() {
            let status = {
                "Connection Test": {
                    text: this.server.status.data,
                },
                "Proxy": {
                    data: {
                        proxy: this.server.server_info.query_result.serverSettings.proxyStatus,
                    },
                    component: proxyStatus,
                },
                "Workers": {
                    data: {
                        workers: this.server.server_info.query_result.serverSettings.workers,
                        server_id: this.server.id,
                    },
                    component: workersStatus,
                },
                "Remote Connections": {
                    data: {
                        connections: this.server.server_info.query_result.connectedServers,
                        row_index: 0,
                    },
                    component: connectionsSummary,
                },
                "User permissions": {
                    data: {
                        perms: this.server.server_info.query_result.serverUser.Role,
                        row_id: 0,
                        context: "serverView"
                    },
                    component: userPerms,
                },
                "Sub-modules": {
                    data: {
                        submodules: this.server.server_info.query_result.serverSettings.moduleStatus,
                    },
                    component: submodulesStatus,
                },
                "ZeroMQ": {
                    data: {
                        status: this.server.server_info.query_result.serverSettings.zmqStatus,
                    },
                    component: zeroMQStatus,
                },
            }
            return status
        },
        infoData: function() {
            let info = {
                "Version": this.server.status.data,
                "MISP UUID": this.server.server_info.query_result.serverSettings.finalSettings.filter((item) => { return item.setting === "MISP.uuid"})[0].value
            }
            return info
        }
    },
    data: function () {
        return {
        }
    }
}
</script>

<style scoped>
</style>
