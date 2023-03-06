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
                            v-b-modal.modal-batch-add
                        >
                        <iconButton
                                text="Batch mode"
                                icon="list-ol"
                            ></iconButton>
                        </b-dropdown-item>
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
                            title="Quick refresh"
                            @click="fullRefresh()"
                        >
                            <i :class="{'fas fa-sync-alt': true, 'fa-spin': fetching_servers_in_progress}" title="Refresh Servers"></i>
                        </b-button>
                        <b-dropdown right variant="primary" size="sm" style="border-left: 1px solid #0069d9">
                            <template v-slot:button-content>
                                <i class="fas fa-list-ul"></i> Actions
                            </template>
                            <b-dropdown-item-button
                                @click="fullRefresh(false)"
                            >
                                <iconButton
                                    text="Full refresh"
                                    icon="sync-alt"
                                ></iconButton>
                            </b-dropdown-item-button>
                        </b-dropdown>
                        <b-dropdown variant="primary" size="sm" :disabled="!haveSelectedServers" right>
                            <template v-slot:button-content>
                                <i class="fas fa-tasks"></i> Selection
                            </template>
                            <b-dropdown-item-button
                                @click="refreshSelected"
                            >
                                <iconButton
                                    text="Refresh selected"
                                    icon="sync-alt"
                                ></iconButton>
                            </b-dropdown-item-button>
                            <b-dropdown-item-button
                                @click="openBatchAPISelectedModal"
                            >
                                <iconButton
                                    text="Batch API"
                                    title="Batch API call on selected servers"
                                    icon="terminal"
                                ></iconButton>
                            </b-dropdown-item-button>
                            <b-dropdown-item-button
                                @click="openDeleteSelectedModal"
                                class="outline-danger"
                            >
                                <iconButton
                                    text="Delete selected"
                                    title="Delete selected servers"
                                    icon="trash"
                                ></iconButton>
                            </b-dropdown-item-button>
                        </b-dropdown>
                    </b-button-group>
                </b-button-toolbar>
           </div>
        </div>
        <b-table 
            striped outlined show-empty small selectable
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
                <sup><b-badge class="ml-auto" variant="primary" :title="`Latest MISP version: ${githubVersion}`">{{ githubVersion }}</b-badge></sup>
            </template>

            <template v-slot:cell(url)="row">
                <b-link :href="row.value" target="_blank" class="text-nowrap">{{ row.value }} <sup class="fa fa-external-link-alt"></sup></b-link>
            </template>

            <template v-slot:cell(server_status)="row">
                <loaderPlaceholder :loading="!row.value._loading">
                    <span
                        :class="{'text-nowrap': true, 'text-danger': row.value.error, 'text-success': !row.value.error}"
                    >
                        <b-icon v-if="row.value.data !== undefined" icon="circle-fill"></b-icon>
                        {{ row.value.data }}
                        <small
                             v-if="row.value.latency !== undefined"
                             :class="{'text-success': row.value.latency < 0.3, 'text-warning': row.value.latency >= 0.3 && row.value.latency < 2, 'text-danger': row.value.latency >= 2}"
                        >
                            {{ row.value.latency.toFixed(3) }}ms
                        </small>
                    </span>
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
                <span class="d-block" style="width: 100px;">
                    <span :class="forcedHidden == row.index ? 'd-none' : 'hide-on-hover'">
                        <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]">
                            <timeSinceRefresh
                                :key="table.timeKey"
                                :timestamp="row.value"
                            ></timeSinceRefresh>
                        </loaderPlaceholder>
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
                            <b-button class="ml-1" size="xs" variant="link" @click="openEditModal(row.item)">
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
                                    :menu="genContextualMenu(row.item.id)"
                                    @handle-refresh-info="handleRefreshInfo"
                                    @view-connections="viewConnections"
                                    @view-in-network="viewInNetwork"
                                    @open-deletion-modal="openDeletionModal"
                                    @run-updates="runUpdates"
                                    @handle-discover-servers-add="handleDiscoverServersAdd"
                                ></contextualMenu>
                            </b-dropdown>
                        </div>
                    </span>
                </span>
            </template>

            <template v-slot:cell(notification)="row">
                <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]">
                    <i
                        class="fas fa-arrow-up text-success"
                        title="Update available"
                        v-if="row.item.canBeUpdated"
                    ></i>
                </loaderPlaceholder>
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
                    <zeroMQStatus :status="row.value"></zeroMQStatus>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(workers)="row">
                <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]">
                    <workersStatus v-if="typeof row.value === 'object'" :workers="row.value" :server_id="row.item.id"></workersStatus>
                </loaderPlaceholder>
            </template>

            <template v-for="field in pluginFields" v-slot:[`cell(${field.key})`]="row">
                <loaderPlaceholder :loading="!server_query_in_progress[row.item.id]" :key="field.key">
                    <pluginIndexColumn
                        v-if="row.value !== undefined"
                        :server_id="row.item.id"
                        :plugin_name="field.key" 
                        :plugin_response="row.value" 
                    ></pluginIndexColumn>
                </loaderPlaceholder>
            </template>

            <template v-slot:row-details="row">
                <RowDetails
                    :server_id="row.item.id"
                    @actionRefresh="handleRefreshInfo({server_id: row.item.id, method: $event})"
                    @actionClose="row.toggleDetails"
                ></RowDetails>
            </template>

            <template v-slot:table-caption>Showing {{ table.totalRows }} out of {{ serverCount }} Servers</template>
        </b-table>

        <DeleteModal
            :serverToDelete="serverToDelete"
            @actionDelete="handleDelete"
        ></DeleteModal>

        <DeleteSelectedModal
            :servers="selectedServers"
            @deletion-success="refreshServerIndex"
        ></DeleteSelectedModal>

        <AddModal
            :modalActionX.sync="modalAddAction"
            :modalAction="modalAddAction"
            :serverForm="validServerToEdit"
            @addition-success="handleAdd"
        ></AddModal>

        <BatchAddModal
            @addition-success="handleBatchAdd"
        ></BatchAddModal>

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
    </div>
</Layout>
</template>

<script>
import store from "@/store/index"
import { mapState, mapGetters } from "vuex"
import Layout from "@/components/layout/Layout.vue"
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"
import userPerms from "@/views/servers/elements/userPerms.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import proxyStatus from "@/views/servers/elements/proxyStatus.vue"
import workersStatus from "@/views/servers/elements/workersStatus.vue"
import submodulesStatus from "@/views/servers/elements/submodulesStatus.vue"
import zeroMQStatus from "@/views/servers/elements/zeroMQStatus.vue"
import pluginIndexColumn from "@/views/servers/elements/pluginIndexColumn.vue"
import connectionsSummary from "@/views/servers/elements/connectionsSummary.vue"
import contextualMenu from "@/components/ui/elements/contextualMenu.vue"
import RowDetails from "@/views/servers/elements/RowDetails.vue"
import DeleteModal from "@/views/servers/DeleteModal.vue"
import BatchAPI from "@/views/servers/BatchAPI.vue"
import DeleteSelectedModal from "@/views/servers/DeleteSelectedModal.vue"
import AddModal from "@/views/servers/AddModal.vue"
import BatchAddModal from "@/views/servers/BatchAddModal.vue"
import CSVAddModal from "@/views/servers/CSVAddModal.vue"
import DiscoverServers from "@/views/servers/DiscoverServers.vue"
import iconButton from "@/components/ui/elements/iconButton.vue"


export default {
    name: "TheServers",
    components: {
        Layout,
        loaderPlaceholder,
        userPerms,
        timeSinceRefresh,
        proxyStatus,
        submodulesStatus,
        zeroMQStatus,
        pluginIndexColumn,
        connectionsSummary,
        contextualMenu,
        workersStatus,
        RowDetails,
        DeleteModal,
        AddModal,
        BatchAddModal,
        CSVAddModal,
        DeleteSelectedModal,
        DiscoverServers,
        iconButton,
        BatchAPI,
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
                        sortable: true
                    },
                    {
                        key: "comment",
                        sortable: true,
                        class: "d-none d-xxl-table-cell",
                    },
                    {
                        key: "url",
                        sortable: false
                    },
                    {
                        key: "server_status",
                        label: "Status",
                        sortable: true,
                        tdClass: "align-middle",
                        formatter: (value, key, item, test) => {
                            return this.server_status[item.id] || null
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
                        sortable: true,
                        class: "align-middle d-none d-xxl-table-cell",
                        formatter: (value, key, item) => {
                            return this.zeromq[item.id] || null
                        }
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
                        key: "last_refresh",
                        sortable: true,
                        class: "align-middle py-0",
                        formatter: (value, key, item) => {
                            return this.last_refresh[item.id] || null
                        }
                    },
                    {
                        key: "notification",
                        label: ""
                    }
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
            githubVersion: state => state.servers.githubVersion,
            selectedServerGroup: state => state.serverGroups.selected,
            servers: state => state.servers.servers,
            server_status: state => state.servers.server_status,
            server_query_in_progress: state => state.servers.server_query_in_progress,
            server_query_error: state => state.servers.server_query_error,
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
        genContextualMenu(server_id) {
            return [
                {
                    variant: "",
                    text: "Refresh",
                    icon: "sync-alt",
                    eventName: "handle-refresh-info",
                    callbackData: {server_id: server_id, method: "no_cache"}
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
                    variant: "outline-primary",
                    disabled: !this.servers[server_id].canBeUpdated,
                    text: "Run updates",
                    icon: "arrow-up",
                    eventName: "run-updates",
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
        handleDelete() {
            this.serverToDelete = {}
            this.refreshServerIndex()
        },
        handleAdd() {
            this.refreshServerIndex()
        },
        handleBatchAdd() {
            this.refreshServerIndex()
        },
        openEditModal(server) {
            this.serverToEdit.formData = JSON.parse(JSON.stringify(server)) // deep clone
            this.modalAddAction = "Edit"
            this.$bvModal.show("modal-add")
        },
        openDeletionModal(data) {
            let server = this.getIndex[data.index]
            this.$bvModal.show("modal-delete")
            this.serverToDelete = server
        },
        handleDiscoverServersAdd(data) {
            this.discoverServersRoot = this.getIndex[data.index]
            this.$bvModal.show("modal-discover-servers-result")
        },
        openDeleteSelectedModal() {
            this.$bvModal.show("modal-delete-selected")
        },
        openBatchAPISelectedModal() {
            this.$bvModal.show("modal-batch-api-selected")
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
        fetchGithubVersion() {
            this.$store.dispatch("servers/fetchGithubVersion")
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch latest version from GitHub",
                        variant: "danger",
                    })
                })
        },
        fetchGithubVersionIfNeeded() {
            if (this.githubVersion.length === 0) {
                this.fetchGithubVersion()
            }
        },
        refreshServerIndex(full=false) {
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
        refreshSelected() {
            this.$store.dispatch("servers/runSelectedConnectionTest", {selection: this.selectedServers})
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not reach Server",
                        variant: "danger",
                    })
                })
            this.$store.dispatch("servers/fetchSelectedServerInfo", {no_cache: true, selection: this.selectedServers})
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch server info",
                        variant: "danger",
                    })
                })
        },
        refreshAllServerOnlineStatus() {
            this.$store.dispatch("servers/runAllConnectionTest")
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not reach Server",
                        variant: "danger",
                    })
                })
        },
        fullRefresh(quick=true) {
            if (quick) {
                this.refreshServerIndex(true)
                    .then(() => {
                        this.refreshAllServerOnlineStatus()
                        this.refreshPluginIndexValues()
                        this.tableQuickRefresh()
                    })
            } else {
                this.refreshServerIndex(true)
                    .then(() => {
                        this.refreshAllServerOnlineStatus()
                        this.refreshPluginIndexValues(true)
                        this.refreshAllInfo(true)
                    })
            }
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
        handleRefreshInfo(data) {
            const server_id = data.server_id
            const method = data.method
            let server = this.servers[server_id]
            this.$store.dispatch("servers/runConnectionTest", server.id)
            this.refreshInfo(server, method == "no_cache")
        },
        refreshInfo(server, no_cache=false) {
            this.$store.dispatch("servers/fetchServerInfo", {server_id: server.id, no_cache: no_cache})
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch server info",
                        variant: "danger",
                    })
                })
        },
        refreshAllInfo(no_cache=false) {
            this.$store.dispatch("servers/fetchAllServerInfo", {no_cache: no_cache})
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch server info",
                        variant: "danger",
                    })
                })
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
    },
    watch: {
        fetching_servers_in_progress: function() {
            this.table.timeKey += 1 // used to force reload of the timeSinceLastRefresh component
        },
        selectedServerGroup: function() {
            this.fullRefresh()
        }
    },
    mounted() {
        this.fullRefreshIfNeeded()
        // this.fetchGithubVersionIfNeeded()
        this.populatePluginFields()
    },
}
</script>

<style>
.table-primary-background {
    background-color: #b8daff;
}
</style>
