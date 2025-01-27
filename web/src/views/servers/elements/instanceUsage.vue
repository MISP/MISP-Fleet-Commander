<template>
    <b-card no-body>
        <b-tabs pills card vertical>
            <b-tab lazy no-body
                title="Usage graphs"
            >
            <div class="pt-1 pr-1 mb-1 text-right text-nowrap">
                <div class="d-flex">
                    <span>
                        <b-link :href="getDashboardURL" target="_blank" class="text-nowrap ml-2 align-middle">
                            View Full Dashboard
                            <sup class="fa fa-external-link-alt"></sup>
                        </b-link>
                    </span>
                    <span class="ml-auto">
                        <strong class="mr-1">Graphs generated</strong>
                        <b-badge variant="light" class="border align-middle">
                            <timeSinceRefresh
                                :timestamp="getMonitoringGraphLastRefresh"
                            ></timeSinceRefresh>
                        </b-badge>
                        <b-button
                            :variant="getGraphRefreshEnqueued ? 'dark' : 'primary'"
                            :disabled="getGraphRefreshEnqueued"
                            size="xs"
                            title="Refresh Graphs"
                            href="#"
                            class="ml-1 px-2"
                            @click="refreshGraphs()"
                        >
                            <span v-if="getGraphRefreshEnqueued">
                                <i class="fas fa-sync-alt fa-spin"></i>
                                Refresh in progress {{ panel_refreshed_count }} / {{ total_panels }}`
                            </span>
                            <span v-else>
                                <i class="fas fa-sync-alt"></i>
                                Full refresh
                            </span>
                        </b-button>
                    </span>
                </div>
            </div>
            <div class="d-flex flex-wrap p-1" style="gap: 0.25rem;">
                <GrafanaRenderedGraph
                    v-for="panel in panels"
                    :key="panel.panel_id"
                    :loadingRequested="getGraphRefreshEnqueued && !all_refreshed_panels.includes(panel.panel_id)"
                    :panelId="panel.panel_id"
                    :graphAltTitle="panel.alt_title"
                    :width="panel.width"
                    :height="panel.height"
                    :server="getServer"
                ></GrafanaRenderedGraph>
            </div>
            </b-tab>

            <b-tab lazy no-body
                title="Usage basic stats"
            >
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
            </b-tab>
        </b-tabs>
    </b-card>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import api from "@/api/servers"
import { websocketMixin } from "@/helpers/websocketMixin"
import GrafanaRenderedGraph from "@/components/ui/elements/GrafanaRenderedGraph.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"

export default {
    name: "instanceUsage",
    mixins: [websocketMixin],
    components: {
        GrafanaRenderedGraph,
        timeSinceRefresh,
    },
    props: {
        server_id: {
            required: true,
            type: Number,
        },
    },
    sockets: {
        SERVER_GRAPH_REFRESH_STATUS: function (data) {
            if (data.server_id == this.server_id) {
                this.panel_refreshed_count = data.status.panel_refreshed_count
                this.total_panels = data.status.total_panels
                this.all_refreshed_panels.push(data.status.last_panel_refreshed)
            }
        }
    },
    data: function () {
        return {
            panels: [],
            panel_refreshed_count: 0,
            total_panels: 0,
            all_refreshed_panels: [],
            grafana_base_url: '',
            grafana_dashboard: '',
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
            server_usage: state => state.servers.server_usage,
            server_publication_activity: state => state.servers.server_publication_activity,
            last_refresh: state => state.servers.last_refresh,
            monitoring_graph_last_refresh: state => state.servers.monitoring_graph_last_refresh,
            server_graphs_refresh_enqueued: state => state.servers.server_graphs_refresh_enqueued,
        }),
        getServer: function () {
            return this.servers[this.server_id]
        },
        getServerUsage: function () {
            return this.server_usage[this.server_id] | {}
        },
        getServerPublicationActivity: function () {
            return this.server_publication_activity[this.server_id]
        },
        getGraphRefreshEnqueued: function() {
            return this.server_graphs_refresh_enqueued[this.server_id]
        },
        getMonitoringGraphLastRefresh: function() {
            return this.monitoring_graph_last_refresh[this.server_id]
        },
        getDashboardURL: function() {
            return `${this.grafana_base_url}/${this.grafana_dashboard}`
        }
    },
    methods: {
        refreshGraphs: function() {
            return new Promise((resolve, reject) => {
                this.all_refreshed_panels = []
                this.wsServerGraphsRefresh(this.server_id)
            })
        },
        getUsageDashboardConfig: function() {
            return api.getUsageDashboardConfig((dashboardConfig) => {
                this.panels = dashboardConfig.panels
                this.grafana_base_url = dashboardConfig.grafana_base_url
                this.grafana_dashboard = dashboardConfig.grafana_dashboard
            })
        },
    },
    mounted: function() {
        this.getUsageDashboardConfig()
    }
}
</script>

<style scoped>

</style>