<template>
<Layout name="LayoutDefault">
    <div>
        <nav class="fleet-tabs" aria-label="Fleet views">
            <router-link
                v-for="tab in fleetTabs"
                :key="tab.name"
                :to="{ query: tabQuery(tab.name) }"
                :class="['fleet-tab', { active: activeTab === tab.name }]"
                :aria-current="activeTab === tab.name ? 'page' : null"
                replace
            >
                <i :class="['fas', `fa-${tab.icon}`, 'mr-1']" aria-hidden="true"></i>{{ tab.label }}
                <span
                    v-if="tab.name === 'baseline' && baselineDriftCount > 0"
                    class="fleet-tab-count"
                    :title="`${baselineDriftCount} drift issue${baselineDriftCount === 1 ? '' : 's'}`"
                >{{ baselineDriftCount }}</span>
            </router-link>
        </nav>

        <div v-if="activeTab === 'jobs'" class="fleet-jobs">
            <JobList v-if="selectedFleet" :fleet-id="selectedFleet.id"></JobList>
        </div>

        <BaselineTab v-if="activeTab === 'baseline' && selectedFleet" :fleet-id="selectedFleet.id"></BaselineTab>

        <FleetUsageTab v-if="activeTab === 'usage' && selectedFleet" :fleet-id="selectedFleet.id"></FleetUsageTab>

        <div v-show="activeTab === 'servers'">
        <div class="table-header">
            <div class="d-flex" style="margin-top: -5px">
                <b-button-group class="text-nowrap mr-2 pb-1">
                    <b-button
                        size="sm"
                        variant="primary"
                        v-b-modal.modal-add
                    >
                        <i class="fas fa-plus"></i> Add servers
                    </b-button>
                    <b-dropdown left variant="primary" size="sm" style="border-left: 1px solid #0069d9">
                        <b-dropdown-item
                            v-b-modal.modal-csv-add
                        >
                            <iconButton
                                text="From CSV"
                                icon="file-csv"
                            ></iconButton>
                        </b-dropdown-item>
                    </b-dropdown>
                </b-button-group>
                <b-pagination
                    class="mb-0"
                    v-model="table.currentPage"
                    size="sm"
                    :per-page="table.perPage"
                    :total-rows="matchingRows"
                    aria-controls="server-table"
                ></b-pagination>
                <b-form-select v-model="table.perPage" :options="table.optionsPerPage" size="sm" class="ml-2"></b-form-select>
                <div class="ml-2 d-flex flex-row align-items-center">
                    <FleetWatchingStatusBadge :show_for_selected_fleet="true" class="mr-1"></FleetWatchingStatusBadge>
                    <MonitoringStatusBadge :show_for_selected_fleet="true"></MonitoringStatusBadge>
                </div>
            </div>
            <div class="table-tools">
                <b-button-toolbar class="justify-content-end flex-nowrap">
                    <b-button
                        size="sm"
                        :variant="table.onlyIssues ? 'secondary' : 'outline-secondary'"
                        :pressed="table.onlyIssues"
                        :disabled="!healthLoaded"
                        class="issues-toggle mr-2 align-self-end"
                        title="Only show servers with unacknowledged issues"
                        @click="table.onlyIssues = !table.onlyIssues"
                    >
                        <i class="fas fa-filter mr-1" aria-hidden="true"></i>With issues
                        <span v-if="healthLoaded" class="issues-toggle-count">{{ serversWithIssuesCount }}</span>
                    </b-button>
                    <b-input-group size="sm" class="px-0 col">
                        <b-form-input
                            v-model="table.filter"
                            type="search"
                            id="filterInput"
                            placeholder="Search name, URL or issue"
                            class="table-search-box border-bottom-0 rounded-top align-self-end"
                            style="border-radius: 0"
                        ></b-form-input>
                    </b-input-group>
                    <b-button-group>
                        <b-button
                            class="ml-2"
                            variant="primary"
                            size="sm"
                            title="Quick refresh - Refresh table, online status and plugin values"
                            @click="fullRefresh()"
                        >
                            <i :class="{'fas fa-sync-alt': true, 'fa-spin': fetching_servers_in_progress}" title="Refresh Servers"></i>
                        </b-button>
                        <b-dropdown right variant="primary" size="sm" style="border-left: 1px solid #0069d9">
                            <template v-slot:button-content>
                                <i class="fas fa-list-ul"></i> Actions
                            </template>
                            <b-dropdown-item-button
                                @click="wsRefresh()"
                            >
                                <iconButton
                                    text="Refresh All Servers"
                                    icon="sync-alt"
                                ></iconButton>
                            </b-dropdown-item-button>
                        </b-dropdown>
                        <b-dropdown variant="primary" size="sm" :disabled="!haveSelectedServers" right>
                            <template v-slot:button-content>
                                <i class="fas fa-tasks"></i> Selection
                            </template>
                            <b-dropdown-item-button
                                @click="wsRefreshSelected"
                            >
                                <iconButton
                                    text="Refresh"
                                    icon="sync-alt"
                                ></iconButton>
                            </b-dropdown-item-button>
                            <b-dropdown-item-button
                                @click="openBatchAPISelectedModal"
                            >
                                <iconButton
                                    text="Batch API"
                                    title="Batch API call"
                                    icon="terminal"
                                ></iconButton>
                            </b-dropdown-item-button>
                            <b-dropdown-item-button
                                @click="openBatchPluginActionSelectedModal"
                            >
                                <iconButton
                                    text="Batch Plugin Action"
                                    title="Batch Plugin Action"
                                    icon="plug"
                                ></iconButton>
                            </b-dropdown-item-button>
                            <b-dropdown-item-button
                                @click="exportSelected"
                            >
                                <iconButton
                                    text="Export selected"
                                    title="Export servers"
                                    icon="upload"
                                ></iconButton>
                            </b-dropdown-item-button>
                            <b-dropdown-item-button
                                @click="openDeleteSelectedModal"
                                class="outline-danger"
                            >
                                <iconButton
                                    text="Delete selected"
                                    title="Delete servers"
                                    icon="trash"
                                ></iconButton>
                            </b-dropdown-item-button>

                            <contextualMenu
                                :menu="genContextualMenuSelectionDropDown()"
                                @exec-quick-action-on-selected="execQuickActionOnSelected"
                            ></contextualMenu>
                        </b-dropdown>
                    </b-button-group>
                </b-button-toolbar>
           </div>
        </div>
        <b-table
            striped outlined show-empty selectable
            :small="serverCount > 16"
            table-class="table-auto-hide-action"
            selected-variant="table-none"
            :tbody-tr-class="rowClass"
            responsive="md"
            id="server-table"
            ref="serverTable"
            :per-page="table.perPage"
            :current-page="table.currentPage"
            :busy.sync="table.isBusy"
            :items="getIndex" 
            :fields="table.fields"
            :filter="tableFilter"
            :filter-function="filterServer"
            :no-provider-paging="true"
            :no-provider-sorting="true"
            :no-provider-filtering="true"
            :sort-icon-left="true"
            @filtered="onFiltered"
            @sort-changed="onSorted"
            @row-selected="onRowSelected"
        >
            <template v-slot:table-busy>
                <div class="text-center text-danger my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong class="ml-2">Loading...</strong>
                </div>
            </template>

            <template v-slot:head(selected)>
                <b-form-checkbox
                    @change="setCheckOnServers"
                ></b-form-checkbox>
            </template>
            <template v-slot:cell(selected)="row">
                <b-form-checkbox
                    v-model="row.rowSelected"
                    @input="selectRow(row.rowSelected, row.index)"
                ></b-form-checkbox>
            </template>

            <template v-slot:head(server_status)>
                Status
            </template>

            <template v-slot:cell(health)="row">
                <ServerHealthBadge :server_id="row.item.id" :fleet_id="selectedFleet ? selectedFleet.id : null"></ServerHealthBadge>
            </template>

            <template v-slot:cell(name)="row">
                <div class="d-flex flex-nowrap align-items-center justify-content-left">
                    <b-img v-if="instancePictures[row.item.id]" :src="instancePictures[row.item.id]" class="instance-picture mr-1"></b-img>
                    <span>{{ row.value }}</span>
                </div>
            </template>

            <template v-slot:cell(url)="row">
                <b-link :href="row.value" target="_blank" class="text-nowrap">{{ row.value }} <sup class="fa fa-external-link-alt"></sup></b-link>
            </template>

            <template v-slot:cell(server_status)="row">
                <span v-show="server_status_refresh_enqueued[row.item.id] && row.value.data === undefined">
                    <i class="fas fa-circle-notch fa-spin"></i>
                </span>
                <loaderPlaceholder :loading="!row.value._loading">
                    <ServerConnectionTestResult :server_id="row.value"></ServerConnectionTestResult>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(user_perm)="row">
                <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]">
                    <userPerms
                        :perms="row.value"
                        :row_id="row.index"
                        context="serverindex"
                    ></userPerms>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(last_refresh)="row">
                <span class="d-block" style="width: 105px;">
                    <span :class="forcedHidden == row.index ? 'd-none' : 'hide-on-hover'">
                        <span>
                            <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]">
                                <timeSinceRefresh
                                    :key="table.timeKey"
                                    :timestamp="row.value"
                                    :server_id="row.item.id"
                                ></timeSinceRefresh>
                            </loaderPlaceholder>
                            <span v-show="server_refresh_enqueued[row.item.id]">
                                <i class="fas fa-circle-notch fa-spin"></i>
                            </span>
                        </span>
                    </span>
                    <span :class="forcedHidden == row.index ? '' : 'reveal-on-hover'">
                        <div class="btn-group">
                            <b-button
                                size="xs" variant ="link"
                                @click="row.toggleDetails"
                            >
                                <i :class="['text-secondary', 'fas', `fa-${row.detailsShowing ? 'compress-alt' : 'expand-alt'}`]"></i>
                            </b-button>
                            <b-link class="ml-1 btn-xs" variant="link" :to="{ name: 'servers.view', params: { server_id: row.item.id } }">
                                <i class="fas fa-eye align-middle"></i>
                            </b-link>
                            <b-button class="ml-1" size="xs" variant="link" @click="openEditModal(row.item.id)">
                                <i class="fas fa-edit"></i>
                            </b-button>
                            <b-dropdown 
                                variant="link" size="xs" class="ml-1"
                                @hidden="clearForcedHidden"
                                right no-caret lazy
                            >
                                <template v-slot:button-content>
                                    <i 
                                        class="fas fa-ellipsis-v"
                                        @click="forceHidden(row.item.id)"
                                    ></i>
                                </template>
                                <contextualMenu
                                    :menu="genContextualMenuRow(row.item.id)"
                                    @handle-wsrefresh-info="handleRefreshInfoWS"
                                    @view-connections="viewConnections"
                                    @view-in-network="viewInNetwork"
                                    @open-deletion-modal="openDeletionModal"
                                    @exec-quick-action="execQuickAction"
                                    @handle-discover-servers-add="handleDiscoverServersAdd"
                                ></contextualMenu>
                            </b-dropdown>
                        </div>
                    </span>
                </span>
            </template>

            <template v-slot:cell(remote_connections)="row">
                <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]">
                    <connectionsSummary
                        v-if="(typeof row.value !== 'string')"
                        :connections="row.value"
                        :server_id="row.item.id"
                        :row_index="row.index"
                    ></connectionsSummary>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(proxy)="row">
                <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]">
                    <proxyStatus :proxy="row.value" :server_id="row.item.id"></proxyStatus>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(submodule)="row">
                <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]">
                    <submodulesStatus :submodules="row.value" :server_id="row.item.id"></submodulesStatus>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(zeromq)="row">
                <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]">
                    <zeroMQStatus :server_id="row.item.id"></zeroMQStatus>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(workers)="row">
                <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]">
                    <workersStatus :workers="row.value" :server_id="row.item.id"></workersStatus>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(usage)="row">
                <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]">
                    <dataUsageShort :server_id="row.item.id"></dataUsageShort>
                </loaderPlaceholder>
            </template>

            <template v-for="field in pluginFields" v-slot:[`cell(${field.key})`]="row">
                <loaderPlaceholder :loading="!fetching_plugin_index_in_progress" :key="field.key">
                    <pluginValueRenderer
                        v-if="row.value"
                        :server_id="row.item.id"
                        :plugin_name="field.key" 
                        :plugin_response="row.value" 
                    ></pluginValueRenderer>
                </loaderPlaceholder>
            </template>

            <template v-slot:row-details="row">
                <RowDetails
                    :server_id="row.item.id"
                    @actionRefresh="handleRefreshInfoWS({server_id: row.item.id})"
                    @actionClose="row.toggleDetails"
                ></RowDetails>
            </template>

            <template v-slot:table-caption>
                <div class="d-flex align-items-center" style="gap: 0.5em;">
                    <span>Showing {{ displayedTotalRows }} out of {{ serverCount }} Servers</span>
                    <b-pagination
                        class="mb-0"
                        v-model="table.currentPage"
                        size="sm"
                        :per-page="table.perPage"
                        :total-rows="matchingRows"
                        aria-controls="server-table"
                    ></b-pagination>
                </div>
            </template>
        </b-table>
        </div>

        <DeleteModal
            :serverToDelete="serverToDelete"
            @actionDelete="handleDelete"
        ></DeleteModal>

        <DeleteSelectedModal
            :servers="selectedServers"
            @deletion-success="getServerIndex"
        ></DeleteSelectedModal>

        <AddModal
            :modalAction.sync="modalAddAction"
            :serverForm="validServerToEdit"
            @addition-success="handleAdd"
        ></AddModal>

        <CSVAddModal
            @addition-success="handleBatchAdd"
        ></CSVAddModal>

        <DiscoverServers
            :rootServer="discoverServersRoot"
            @addition-success="handleBatchAdd"
        ></DiscoverServers>

        <BatchAPI
            :server_ids="selectedServerIDs"
        ></BatchAPI>

        <BatchPluginAction
            :server_ids="selectedServerIDs"
        ></BatchPluginAction>
    </div>
</Layout>
</template>

<script>
import pluginAPI from "@/api/plugins"
import Vue from "vue"
import api from "@/api/servers"
import { websocketMixin } from "@/helpers/websocketMixin"
import { mapState, mapGetters } from "vuex"
import Layout from "@/components/layout/Layout.vue"
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"
import userPerms from "@/views/servers/elements/userPerms.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import proxyStatus from "@/views/servers/elements/proxyStatus.vue"
import workersStatus from "@/views/servers/elements/workersStatus.vue"
import dataUsageShort from "@/views/servers/elements/dataUsageShort.vue"
import submodulesStatus from "@/views/servers/elements/submodulesStatus.vue"
import zeroMQStatus from "@/views/servers/elements/zeroMQStatus.vue"
import ServerConnectionTestResult from "@/components/ui/elements/ServerConnectionTestResult.vue"
import pluginValueRenderer from "@/views/servers/elements/pluginValueRenderer.vue"
import connectionsSummary from "@/views/servers/elements/connectionsSummary.vue"
import contextualMenu from "@/components/ui/elements/contextualMenu.vue"
import RowDetails from "@/views/servers/elements/RowDetails.vue"
import DeleteModal from "@/views/servers/DeleteModal.vue"
import BatchAPI from "@/views/servers/BatchAPI.vue"
import DeleteSelectedModal from "@/views/servers/DeleteSelectedModal.vue"
import AddModal from "@/views/servers/AddModal.vue"
import BatchPluginAction from "@/views/servers/BatchPluginAction.vue"
import { startedToastId } from "@/components/jobs/JobNotifier.vue"
import { isFinalJob } from "@/helpers/jobs"
import CSVAddModal from "@/views/servers/CSVAddModal.vue"
import DiscoverServers from "@/views/servers/DiscoverServers.vue"
import iconButton from "@/components/ui/elements/iconButton.vue"
import MonitoringStatusBadge from "@/components/ui/elements/MonitoringStatusBadge.vue"
import FleetWatchingStatusBadge from "@/components/ui/elements/FleetWatchingStatusBadge.vue"
import ServerHealthBadge from "@/components/health/ServerHealthBadge.vue"
import { EMPTY_DIGEST } from "@/store/modules/health"
import JobList from "@/components/jobs/JobList.vue"
import BaselineTab from "@/components/baselines/BaselineTab.vue"
import FleetUsageTab from "@/components/usage/FleetUsageTab.vue"

// Instance pictures by server ID (a data URI, or "" for none), asked for once per session and shared by every
// fleet page. Each one is a request that may reach the MISP server: a few at a time, so that they never hold up
// the browser's connections to the API (with 51 servers they delayed the plugin values and the rest of the page)
const instancePictures = Vue.observable({})
const instancePicturesPending = new Set()
const INSTANCE_PICTURE_CONCURRENCY = 2

// The fleet page's views, opened with `?tab=` (Servers when absent)
const FLEET_TABS = [
    { name: "servers", label: "Servers", icon: "server" },
    { name: "baseline", label: "Baseline", icon: "ruler-combined" },
    { name: "usage", label: "Usage", icon: "chart-line" },
    { name: "jobs", label: "Jobs", icon: "list-check" },
]

export default {
    name: "TheServers",
    mixins: [websocketMixin],
    components: {
        Layout,
        loaderPlaceholder,
        userPerms,
        timeSinceRefresh,
        proxyStatus,
        submodulesStatus,
        zeroMQStatus,
        ServerConnectionTestResult,
        pluginValueRenderer,
        connectionsSummary,
        contextualMenu,
        workersStatus,
        dataUsageShort,
        RowDetails,
        DeleteModal,
        AddModal,
        CSVAddModal,
        DeleteSelectedModal,
        DiscoverServers,
        iconButton,
        BatchAPI,
        BatchPluginAction,
        MonitoringStatusBadge,
        FleetWatchingStatusBadge,
        ServerHealthBadge,
        JobList,
        BaselineTab,
        FleetUsageTab,
    },
    data: function() {
        return {
            fleetTabs: FLEET_TABS,
            postInProgress: {
                modal: false,
            },
            modalAddAction: "Add",
            serverToDelete: {},
            serverToEdit: { formData: {}}, // nested cheat to keep it reactive
            discoverServersRoot: {},
            forcedHidden: -1,
            table: {
                timeKey: 0,
                isBusy: false,
                filtered: "",
                filter: null,
                onlyIssues: false,
                totalRows: 0,
                currentPage: 1,
                perPage: 30,
                optionsPerPage: [{ text: 30, value: 30 }, { text: 50, value: 50 }, { text: 100, value: 100 }],
                fields: [
                    {
                        key: "selected",
                        label: ""
                    },
                    {
                        key: "health",
                        label: "Health",
                        sortable: true,
                        sortByFormatted: true,
                        sortDirection: "desc", // first click: most severe first
                        class: "align-middle",
                        headerTitle: "Most severe unacknowledged issue, and how many there are",
                        formatter: (value, key, item) => {
                            return this.healthSortKey(item.id)
                        }
                    },
                    {
                        key: "name",
                        sortable: true,
                        class: "align-middle",
                    },
                    {
                        key: "comment",
                        sortable: true,
                        class: "d-none d-xxl-table-cell align-middle",
                    },
                    {
                        key: "url",
                        sortable: true,
                        class: "align-middle",
                    },
                    {
                        key: "server_status",
                        label: "Status",
                        sortable: true,
                        class: "align-middle",
                        tdClass: "align-middle",
                        formatter: (value, key, item, test) => {
                            return item.id || null
                        }
                    },
                    {
                        key: "user_perm",
                        label: "User perms",
                        sortable: true,
                        class: "align-middle d-none d-xl-table-cell",
                        formatter: (value, key, item) => {
                            return this.server_user[item.id] ? (this.server_user[item.id]['Role'] || null) : null
                        }
                    },
                    {
                        key: "remote_connections",
                        label: "Remote Connections",
                        sortable: true,
                        class: "align-middle d-none d-xl-table-cell",
                        formatter: (value, key, item) => {
                            return this.remote_connections[item.id] ? Object.values(this.remote_connections[item.id]) : null
                        }
                    },
                    {
                        key: "submodule",
                        label: "Sub-modules",
                        sortable: true,
                        class: "align-middle d-none d-xxl-table-cell",
                        formatter: (value, key, item) => {
                            return this.submodules[item.id] || null
                        }
                    },
                    {
                        key: "proxy",
                        label: "Proxy",
                        sortable: true,
                        class: "align-middle d-none d-xxl-table-cell",
                        formatter: (value, key, item) => {
                            return this.proxy[item.id] || null
                        }
                    },
                    {
                        key: "zeromq",
                        label: "ZeroMQ",
                        class: "align-middle d-none d-xxl-table-cell",
                    },
                    {
                        key: "workers",
                        label: "Workers",
                        sortable: true,
                        class: "align-middle d-none d-md-table-cell",
                        formatter: (value, key, item) => {
                            return this.workers[item.id] || null
                        }
                    },
                    {
                        key: "usage",
                        label: "Usage",
                        sortable: false,
                        class: "align-middle d-none d-xxl-table-cell",
                    },
                    {
                        key: "last_refresh",
                        sortable: true,
                        class: "align-middle py-0",
                        formatter: (value, key, item) => {
                            return this.last_refresh[item.id] || null
                        }
                    },
                ],
            },
            pluginFields: [],
            tableItems: [],
            selectedServers: [],
            selectedServerIDs: [],
        }
    },
    computed: {
        activeTab() {
            const tab = this.$route.query.tab
            return FLEET_TABS.some(entry => entry.name === tab) ? tab : "servers"
        },
        ...mapState({
            fetching_servers_in_progress: state => state.servers.fetching_servers_in_progress,
            fetching_plugin_index_in_progress: state => state.plugins.fetching_index_in_progress,
            selectedFleet: state => state.fleets.selected,
            servers: state => state.servers.servers,
            server_status: state => state.servers.server_status,
            server_query_in_progress: state => state.servers.server_query_in_progress,
            server_status_refresh_enqueued: state => state.servers.server_status_refresh_enqueued,
            server_query_error: state => state.servers.server_query_error,
            server_refresh_enqueued: state => state.servers.server_refresh_enqueued,
            server_user: state => state.servers.server_user,
            remote_connections: state => state.servers.remote_connections,
            submodules: state => state.servers.submodules,
            proxy: state => state.servers.proxy,
            zeromq: state => state.servers.zeromq,
            workers: state => state.servers.workers,
            pluginValues: state => state.plugins.pluginIndexValues,
            server_users: state => state.servers.server_users,
            last_refresh: state => state.servers.last_refresh,
            diagnostic_full: state => state.servers.diagnostic_full,
            healthLoaded: state => state.health.loaded,
            healthDigests: state => state.health.digests,
        }),
        ...mapGetters({
            serverCount: "servers/serverCount",
            getServerList: "servers/getServerList",
            indexPlugins: "plugins/indexPlugins",
            quickActionPlugins: "plugins/quickActionPlugins",
        }),
        getIndex() {
            return (this.getServerList || []).map(server => ({ ...server }))
        },
        instancePictures() {
            return instancePictures
        },
        validServerToEdit() {
            return this.serverToEdit.formData
        },
        haveSelectedServers() {
            return this.selectedServers.length > 0
        },
        getSelectedServer() {
            return Array.from(this.selectedServers)
        },
        getSelectedServerIDs() {
            return Array.from(this.selectedServerIDs)
        },
        // Rows the table can show: every server of the fleet, or those the search and filters keep (the table tells
        // that count when it filters). Derived, so it is right however the servers were loaded
        matchingRows() {
            return this.tableFilter === null ? this.serverCount : this.table.totalRows
        },
        displayedTotalRows() {
            return Math.min(this.matchingRows, this.table.perPage)
        },
        // Open drift issues of the fleet's servers, on the Baseline tab
        baselineDriftCount() {
            return this.getIndex.reduce((count, server) => count + this.activeIssuesOf(server.id)
                .filter(issue => issue.rule === "baseline_drift" && !issue.id.endsWith(":unchecked")).length, 0)
        },
        serversWithIssuesCount() {
            return this.getIndex.filter(server => this.activeIssuesOf(server.id).length > 0).length
        },
        // IDs of the servers to show, or null when nothing filters the table.
        // Recomputed on live health updates, but the table only re-filters (and clears its selection)
        // when the set of matching servers actually changes.
        matchingServerIds() {
            const search = (this.table.filter || "").trim().toLowerCase().replace(/\s+/g, " ")
            if (search === "" && !this.table.onlyIssues) {
                return null
            }
            return this.getIndex
                .filter((server) => {
                    const issues = this.activeIssuesOf(server.id)
                    if (this.table.onlyIssues && issues.length === 0) {
                        return false
                    }
                    if (search === "") {
                        return true
                    }
                    const haystack = [server.name, server.url].concat(issues.map(issue => issue.title))
                    return haystack.some(text => String(text || "").toLowerCase().includes(search))
                })
                .map(server => server.id)
        },
        tableFilter() {
            return this.matchingServerIds === null ? null : { ids: this.matchingServerIds.join(",") }
        },
    },
    methods: {
        tabQuery(name) {
            const query = Object.assign({}, this.$route.query)
            if (name === "servers") {
                delete query.tab
            } else {
                query.tab = name
            }
            return query
        },
        setCheckOnServers(checked) {
            if (checked) {
                this.$refs.serverTable.selectAllRows()
            } else {
                this.$refs.serverTable.clearSelected()
            }
        },
        onRowSelected(items) {
            this.selectedServers = items.map(server => server)
            this.selectedServerIDs = items.map(server => server.id)
        },
        selectRow(checked, index) {
            if (checked) {
                this.$refs.serverTable.selectRow(index)
            } else {
                this.$refs.serverTable.unselectRow(index)
            }
        },
        filterServer(server, criteria) {
            return criteria.ids.split(",").includes(String(server.id))
        },
        activeIssuesOf(server_id) {
            return (this.healthDigests[server_id] || EMPTY_DIGEST).active
        },
        // Most severe first when sorted descending: criticals, then warnings, then info, by count
        healthSortKey(server_id) {
            if (!this.healthLoaded) {
                return -1
            }
            return (this.healthDigests[server_id] || EMPTY_DIGEST).weight
        },
        onFiltered(filteredItems) {
            this.table.totalRows = filteredItems.length
            // Live health updates may shrink the list: stay on the current page while it exists
            const lastPage = Math.max(1, Math.ceil(filteredItems.length / this.table.perPage))
            this.table.currentPage = Math.min(this.table.currentPage, lastPage)
        },
        onSorted() {
            this.table.currentPage = 1
        },
        genContextualMenuRow(server_id) {
            const contextualMenu = [
                {
                    variant: "",
                    text: "Refresh",
                    icon: "sync-alt",
                    eventName: "handle-wsrefresh-info",
                    callbackData: {server_id: server_id}
                },
                {
                    variant: "",
                    text: "View connections",
                    icon: "network-wired",
                    eventName: "view-connections",
                    callbackData: {server_id: server_id}
                },
                {
                    variant: "",
                    text: "View network",
                    icon: "project-diagram",
                    eventName: "view-in-network",
                    callbackData: {server_id: server_id}
                },
                {
                    variant: "",
                    text: "Discover servers",
                    title: "Discover connected servers",
                    icon: "radar",
                    useAsset: true,
                    eventName: "handle-discover-servers-add",
                    callbackData: {server_id: server_id}
                },
                {
                    variant: "outline-danger",
                    text: "Delete server",
                    icon: "trash",
                    eventName: "open-deletion-modal",
                    callbackData: {server_id: server_id}
                },
            ]

            contextualMenu.push(
                {
                    is_header: true,
                    text: 'Plugin Quick Action',
                    icon: "bolt",
                }
            )
            this.quickActionPlugins.forEach((plugin) => {
                contextualMenu.push(
                    {
                        variant: plugin.quickActionMeta.quickActionVariant,
                        text: plugin.quickActionMeta.quickActionName,
                        icon: plugin.quickActionMeta.quickActionIcon,
                        eventName: "exec-quick-action",
                        callbackData: {server_id: server_id, plugin: plugin}
                    }
                )
            })
            return contextualMenu
        },
        genContextualMenuSelectionDropDown() {
            const contextualMenu = [
                {
                    is_header: true,
                    text: 'Plugin Quick Action',
                    icon: "bolt",
                }
            ]
            this.quickActionPlugins.forEach((plugin) => {
                contextualMenu.push(
                    {
                        variant: plugin.quickActionMeta.quickActionVariant,
                        text: plugin.quickActionMeta.quickActionName,
                        icon: plugin.quickActionMeta.quickActionIcon,
                        eventName: "exec-quick-action-on-selected",
                        callbackData: {plugin: plugin}
                    }
                )
            })
            return contextualMenu
        },
        rowClass(item, type) {
            let classes = ["no-outline"]
            if ((type == "row" || type == "row-details") && item && item._showDetails) {
                classes.push("table-primary-background")
            }
            return classes
        },
        forceHidden(row_id) {
            this.forcedHidden = row_id
        },
        clearForcedHidden() {
            this.forcedHidden = -1
        },
        formatErrorMessage(message) {
            if (message === undefined) {
                return ''
            }
            if (message.startsWith('Authentication failed')) {
                return 'Authentication failed'
            }
            if (message.includes('Connection Error:')) {
                return message.match(/\[([^\]]+)\]/)?.[1] || message
            }
            return message
        },
        handleDelete() {
            this.serverToDelete = {}
            this.getServerIndex()
        },
        handleAdd() {
            this.getServerIndex()
        },
        handleBatchAdd() {
            this.getServerIndex()
        },
        resetModalAction() {
            this.modalAddAction = "Add"
        },
        openEditModal(server_id) {
            const server = this.servers[server_id]
            this.serverToEdit.formData = JSON.parse(JSON.stringify(server)) // deep clone
            this.modalAddAction = "Edit"
            this.$bvModal.show("modal-add")
        },
        openDeletionModal(data) {
            const server = this.servers[data.server_id]
            this.$bvModal.show("modal-delete")
            this.serverToDelete = server
        },
        handleDiscoverServersAdd(data) {
            this.discoverServersRoot = this.servers[data.server_id]
            this.$bvModal.show("modal-discover-servers-result")
        },
        openDeleteSelectedModal() {
            this.$bvModal.show("modal-delete-selected")
        },
        openBatchAPISelectedModal() {
            this.$bvModal.show("modal-batch-api-selected")
        },
        openBatchPluginActionSelectedModal() {
            this.$bvModal.show("modal-batch-plugin-action-selected")
        },
        viewConnections(data) {
            return data
        },
        viewInNetwork(data) {
            return data
        },
        runUpdates(data) {
            return data
        },
        getServerIndex() {
            this.table.isBusy = true
            return new Promise((resolve, reject) => {
                this.$store.dispatch("servers/fetchServers", {force: true})
                    .then(() => {
                        this.table.totalRows = this.serverCount
                        resolve()
                    })
                    .catch(error => {
                        this.$bvToast.toast(error, {
                            title: "Could not fetch server index",
                            variant: "danger",
                        })
                        reject()
                    })
                    .finally(() => {
                        this.table.isBusy = false
                    })
            })
        },
        wsRefreshSelected() {
            this.getSelectedServerIDs.forEach((serverID) => {
                this.wsServerRefresh(serverID)
            })
        },
        wsRefreshAllServerOnlineStatus() {
            this.wsFleetConnectionTest(this.selectedFleet.id)
        },
        wsRefresh() {
            this.wsFleetRefresh(this.selectedFleet.id)
        },
        fullRefresh() {
            this.getServerIndex()
                .then(() => {
                    this.wsRefreshAllServerOnlineStatus()
                    this.refreshPluginIndexValues()
                    this.tableQuickRefresh()
                })
        },
        fullRefreshIfNeeded() {
            if (this.serverCount === 0) {
                this.fullRefresh()
            }
        },
        tableQuickRefresh() {
            if (this.$refs.serverTable !== undefined) {
                this.$refs.serverTable.refresh()
            }
        },
        handleRefreshInfoWS(data) {
            const server_id = data.server_id
            this.wsServerRefresh(server_id)
        },
        refreshPluginIndexValues(no_cache=false) {
            this.$store.dispatch("plugins/fetchIndexValues", {no_cache: no_cache})
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch plugin values",
                        variant: "danger",
                    })
                })
        },
        populatePluginFields() {
            // Safe to run again when the plugin list or the enabled plugins arrive: previous plugin columns go first
            this.table.fields = this.table.fields.filter(field => !this.pluginFields.includes(field))
            this.pluginFields = []
            const lastRefreshPosition = this.table.fields.indexOf('last_refresh')
            this.indexPlugins.forEach(plugin => {
                const field = {
                    key: plugin.id,
                    label: plugin.name,
                    formatter: (value, key, item) => {
                        return this.pluginValues[item.id] ? (this.pluginValues[item.id][plugin.id] || null) : null
                    },
                    headerTitle: plugin.description,
                    sortable: true,
                    sortByFormatted: true,
                    tdClass: "align-middle",
                }
                this.pluginFields.push(field)
                this.table.fields.splice(lastRefreshPosition - 1, 0, field)
            })
        },
        getToastVariant(state) {
            if (state == 'success') {
                return 'success'
            } else if (state == 'fail' || state == 'error') {
                return 'danger'
            }
            return 'primary'
        },
        execQuickAction({server_id, plugin}) {
            const form_data = {}
            pluginAPI.submitQuickAction(server_id, plugin.id, form_data)
                .then((response) => {
                    if (response.data.error) {
                        const errorMessage = Array.isArray(response.data.error) ? response.data.error.join(', ') : response.data.error
                        this.$bvToast.toast(errorMessage, {
                            title: `Failure while executing quick action ${plugin.quickActionMeta.quickActionName}`,
                            variant: "danger",
                        })
                    } else {
                        const successMessage = response.data.data.message
                        this.$bvToast.toast(successMessage, {
                            title: `Successfully executed quick action ${plugin.quickActionMeta.quickActionName}`,
                            variant: this.getToastVariant(response.data.status),
                        })
                    }
                })
                .catch(error => {
                    const errorMessage = error.toJson()
                    this.$bvToast.toast(errorMessage, {
                        title: `Could not perform quick action ${plugin.quickActionMeta.quickActionName}`,
                        variant: "danger",
                    })
                })
        },
        // A job: the toast follows it, and the job page has each server's result
        execQuickActionOnSelected({plugin}) {
            const server_ids = this.getSelectedServer.map(server => server.id)
            const name = plugin.quickActionMeta.quickActionName
            return this.$store.dispatch("jobs/create", {
                kind: "plugin_quick_action",
                server_ids,
                params: { plugin_id: plugin.id },
            })
                .then((job) => {
                    if (isFinalJob(this.$store.getters["jobs/job"](job.id))) {
                        return  // Already over: the notifier announces the outcome
                    }
                    const h = this.$createElement
                    this.$bvToast.toast(h("div", [
                        h("b-spinner", { props: { small: true }, class: "mr-2" }),
                        `Running on ${server_ids.length} server${server_ids.length === 1 ? "" : "s"}. You will be told when it ends.`,
                    ]), {
                        id: startedToastId(job.id),
                        title: name,
                        variant: "info",
                        to: { name: "jobs.view", params: { job_id: job.id } },
                        noAutoHide: true,
                        solid: true,
                    })
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: `Could not start quick action ${name}`,
                        variant: "danger",
                    })
                })
        },
        exportSelected() {
            let csv = ''
            // Authkeys never leave the backend, so the export doesn't contain them
            const fields = ['name', 'comment', 'url', 'skip_ssl']
            this.getSelectedServer.forEach((server) => {
                csv += fields.map((f) => server[f]).join(',') + '\n'
            })
            csv = fields.join(',') + '\n' + csv
            const toastContent = this.$createElement('textarea', {class: ['form-control form-control-sm'], attrs: {rows: Math.min(10, this.getSelectedServerIDs.length)}}, csv)
            this.$bvToast.toast(toastContent, {
                title: "Exported servers",
                variant: "info",
                "no-auto-hide": true,
            })
        },
        getInstancePictures() {
            const queue = []
            this.getIndex.forEach((server) => {
                if (instancePictures[server.id] === undefined && !instancePicturesPending.has(server.id)) {
                    instancePicturesPending.add(server.id)
                    queue.push(server.id)
                }
            })
            const next = () => {
                const server_id = queue.shift()
                if (server_id === undefined) {
                    return
                }
                let answered = false
                const done = (picture) => {
                    if (answered) {
                        return
                    }
                    answered = true
                    // A data URI, or '' when the server has no picture or it could not be read
                    Vue.set(instancePictures, server_id, typeof picture === "string" && picture.startsWith("data:image/") ? picture : "")
                    instancePicturesPending.delete(server_id)
                    next()
                }
                api.getInstancePicture(server_id, done, () => done(""))
            }
            for (let i = 0; i < INSTANCE_PICTURE_CONCURRENCY; i++) {
                next()
            }
        },
    },
    watch: {
        indexPlugins(newPlugins, oldPlugins) {
            const ids = plugins => plugins.map(plugin => plugin.id).join(",")
            if (ids(newPlugins) !== ids(oldPlugins)) {
                this.populatePluginFields()
            }
        },
        "table.filter": function() {
            this.table.currentPage = 1
        },
        "table.onlyIssues": function() {
            this.table.currentPage = 1
        },
        fetching_servers_in_progress: function() {
            this.table.timeKey += 1 // used to force reload of the timeSinceLastRefresh component
        },
        selectedFleet: function() {
            this.fullRefresh()
        },
        getIndex: function() {
            this.getInstancePictures()
        },
    },
    mounted() {
        this.fullRefreshIfNeeded()
        // The plugin columns, quick actions and batch plugin actions need the plugin list, which only the server
        // page and the plugin index loaded: a fleet page opened first had none of them
        this.$store.dispatch("plugins/getPlugins", {use_cache: true})
            .catch(() => {})
            .finally(() => {
                this.populatePluginFields()
            })
        this.getInstancePictures()
    },
}
</script>

<style>
.table-primary-background {
    background-color: #b8daff;
}
</style>

<style scoped>
/* Logos come in any shape (MISP 3's is wide, older ones square): same height, width capped */
.instance-picture {
    height: 32px;
    max-width: 96px;
    object-fit: contain;
    flex-shrink: 0;
}

.fleet-tabs {
    display: flex;
    gap: 0.25rem;
    border-bottom: 1px solid var(--health-rule);
    margin: -0.25rem 0 0.85rem;
}

.fleet-tab {
    display: inline-flex;
    align-items: center;
    padding: 0.4rem 0.85rem;
    margin-bottom: -1px;
    border-bottom: 2px solid transparent;
    font-size: 0.9rem;
    font-weight: 600;
    color: #5a6270;
    text-decoration: none;
}

.fleet-tab:hover {
    color: var(--var-color-yankeesblue);
    text-decoration: none;
}

.fleet-tab.active {
    color: var(--var-color-yankeesblue);
    border-bottom-color: var(--var-color-lapislazuli);
}

.fleet-tab:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: -2px;
}

/* Four tabs fit a phone once their icons go */
@media (max-width: 480px) {
    .fleet-tab {
        padding: 0.4rem 0.6rem;
    }

    .fleet-tab > .fas {
        display: none;
    }
}

.fleet-jobs {
    max-width: 1180px;
}

.fleet-tab-count {
    margin-left: 0.4rem;
    min-width: 1.4em;
    padding: 0 0.35rem;
    border-radius: 0.7rem;
    background: var(--health-critical-tint);
    color: var(--health-critical-ink);
    font-size: 0.72rem;
    line-height: 1.5;
    text-align: center;
    font-variant-numeric: tabular-nums;
}

/* The tools wrap below the pagination when both do not fit */
.table-header {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: flex-end;
    column-gap: 1rem;
    row-gap: 0.5rem;
}

.table-tools {
    flex: 0 1 30rem;
    margin-left: auto;
}

.table-tools .input-group {
    min-width: 11rem;
}

.issues-toggle {
    white-space: nowrap;
}

.issues-toggle-count {
    display: inline-block;
    min-width: 1.3em;
    margin-left: 0.3rem;
    padding: 0 0.3rem;
    border-radius: 0.6rem;
    background: rgba(0, 0, 0, 0.08);
    font-size: 0.75rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

.issues-toggle.active .issues-toggle-count {
    background: rgba(255, 255, 255, 0.25);
}
</style>
