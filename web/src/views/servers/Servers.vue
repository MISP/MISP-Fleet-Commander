<template>
<Layout name="LayoutDefault">
    <div>
        <div class="d-flex justify-content-between">
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
                    :total-rows="table.totalRows"
                    aria-controls="server-table"
                ></b-pagination>
                <b-form-select v-model="table.perPage" :options="table.optionsPerPage" size="sm" class="ml-2"></b-form-select>
                <div class="ml-2 d-flex flex-row align-items-center">
                    <FleetWatchingStatusBadge :show_for_selected_fleet="true" class="mr-1"></FleetWatchingStatusBadge>
                    <MonitoringStatusBadge :show_for_selected_fleet="true"></MonitoringStatusBadge>
                </div>
            </div>
            <div class="w-25">
                <b-button-toolbar class="justify-content-end flex-nowrap">
                    <b-input-group size="sm" class="px-0 col">
                        <b-form-input
                            v-model="table.filter"
                            type="search"
                            id="filterInput"
                            placeholder="Type to Search"
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
            :filterIncludedFields="table.filterFields"
            :filter="table.filter"
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
                        :row_index="row.index"
                    ></connectionsSummary>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(proxy)="row">
                <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]">
                    <proxyStatus :proxy="row.value"></proxyStatus>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(submodule)="row">
                <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]">
                    <submodulesStatus :submodules="row.value"></submodulesStatus>
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
                        :total-rows="table.totalRows"
                        aria-controls="server-table"
                    ></b-pagination>
                </div>
            </template>
        </b-table>

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
import store from "@/store/index"
import pluginAPI from "@/api/plugins"
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
import CSVAddModal from "@/views/servers/CSVAddModal.vue"
import DiscoverServers from "@/views/servers/DiscoverServers.vue"
import iconButton from "@/components/ui/elements/iconButton.vue"
import MonitoringStatusBadge from "@/components/ui/elements/MonitoringStatusBadge.vue"
import FleetWatchingStatusBadge from "@/components/ui/elements/FleetWatchingStatusBadge.vue"


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
    },
    data: function() {
        return {
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
                totalRows: 0,
                currentPage: 1,
                perPage: 30,
                optionsPerPage: [{ text: 30, value: 30 }, { text: 50, value: 50 }, { text: 100, value: 100 }],
                filterFields: ["name", "url"],
                fields: [
                    {
                        key: "selected",
                        label: ""
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
        displayedTotalRows() {
            return Math.min(this.table.totalRows, this.table.perPage)
        }
    },
    methods: {
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
        onFiltered(filteredItems) {
            this.table.totalRows = filteredItems.length
            this.table.currentPage = 1
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
        execQuickActionOnSelected({plugin}) {
            const promises = []
            this.getSelectedServer.forEach((server) => {
                const form_data = {}
                const prom = pluginAPI.submitQuickAction(server.id, plugin.id, form_data)
                promises.push(prom)
            })
            return Promise.all(promises)
                .then((responses) => {
                    const successes = responses.filter(response => {
                        return !response.data.error
                    });
                    const failures = responses.filter(response => {
                        return response.data.error
                    });
                    if (successes.length > 0) {
                        const successMessage = successes[0].data.data.message
                        this.$bvToast.toast(successMessage, {
                            title: `Successfully performed ${successes.length} quick action${successes.length > 1 ? 's' : ''}`,
                            variant: "success",
                        })
                    }
                    if (failures.length > 0) {
                        const errorMessage = Array.isArray(failures[0].data.error) ? failures[0].data.error.join(', ') : failures[0].data.error
                        this.$bvToast.toast(errorMessage, {
                            title: `Could not perform ${failures.length} quick action${failures.length > 1 ? 's' : ''}`,
                            variant: "danger",
                        })
                    }
                })
                .catch(error => {
                    const errorMessage = error.toJSON().message
                    this.$bvToast.toast(errorMessage, {
                        title: "Could not perform quick action",
                        variant: "danger",
                    })
                })
        },
        exportSelected() {
            let csv = ''
            const fields = ['name', 'comment', 'url', 'authkey', 'skip_ssl']
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
    },
    watch: {
        fetching_servers_in_progress: function() {
            this.table.timeKey += 1 // used to force reload of the timeSinceLastRefresh component
        },
        selectedFleet: function() {
            this.fullRefresh()
        }
    },
    mounted() {
        this.fullRefreshIfNeeded()
        this.populatePluginFields()
    },
}
</script>

<style>
.table-primary-background {
    background-color: #b8daff;
}
</style>
