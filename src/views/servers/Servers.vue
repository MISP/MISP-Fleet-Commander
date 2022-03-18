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
                    <b-input-group size="sm" class="px-0 col" style="min-width: 200px;">
                        <b-form-input
                            v-model="table.filter"
                            type="search"
                            id="filterInput"
                            placeholder="Type to Search"
                            class="border-bottom-0 rounded-top align-self-end"
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
                            <i :class="{'fas fa-sync-alt': true, 'fa-spin': refreshInProgress}" title="Refresh Servers"></i>
                        </b-button>
                        <b-dropdown right text="Actions" variant="primary" size="sm" style="border-left: 1px solid #0069d9">
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

            <template v-slot:head(status)>
                Status
                <sup><b-badge class="ml-auto" variant="primary" :title="`Latest MISP version: ${githubVersion}`">{{ githubVersion }}</b-badge></sup>
            </template>

            <template v-slot:cell(url)="row">
                <b-link :href="row.value" target="_blank" class="text-nowrap">{{ row.value }} <sup class="fa fa-external-link-alt"></sup></b-link>
            </template>

            <template v-slot:cell(status)="row">
                <loaderPlaceholder :loading="!row.value._loading">
                    <span
                        :class="{'text-nowrap': true, 'text-danger': row.value.error, 'text-success': !row.value.error}"
                    >
                        <b-icon v-if="row.value.data !== undefined" icon="circle-fill"></b-icon>
                        {{ row.value.data }}
                        <small
                             v-if="row.value.data !== undefined"
                             :class="{'text-success': row.value.latency < 0.3, 'text-warning': row.value.latency >= 0.3 && row.value.latency < 1, 'text-danger': row.value.latency >= 1}"
                        >
                            {{ row.value.latency.toFixed(3) }}ms
                        </small>
                    </span>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(server_info.query_result.serverUser.Role)="row">
                <loaderPlaceholder :loading="!row.item.server_info._loading">
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
                        <loaderPlaceholder :loading="!row.value._loading">
                            <timeSinceRefresh
                                :key="table.timeKey"
                                :timestamp="row.value.timestamp"
                            ></timeSinceRefresh>
                        </loaderPlaceholder>
                    </span>
                    <span :class="forcedHidden == row.index ? '' : 'reveal-on-hover'">
                        <div class="btn-group">
                            <b-button
                                size="xs" variant ="link"
                                @click="toggleServerInfo(row.item, row.index, row)"
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
                                        @click="forceHidden(row.index)"
                                    ></i>
                                </template>
                                <contextualMenu
                                    :menu="genContextualMenu(row.index)"
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
                <loaderPlaceholder :loading="!row.item.server_info._loading">
                    <i
                        class="fas fa-arrow-up text-success"
                        title="Update available"
                        v-if="row.item.canBeUpdated"
                    ></i>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(server_info.query_result.connectedServers)="row">
                <loaderPlaceholder :loading="!row.item.server_info._loading">
                    <connectionsSummary
                        v-if="typeof row.value !== 'string'"
                        :connections="row.value"
                        :row_index="row.index"
                    ></connectionsSummary>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(server_info.query_result.serverSettings.proxyStatus)="row">
                <loaderPlaceholder :loading="!row.item.server_info._loading">
                    <proxyStatus :proxy="row.value"></proxyStatus>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(server_info.query_result.serverSettings.moduleStatus)="row">
                <loaderPlaceholder :loading="!row.item.server_info._loading">
                    <submodulesStatus :submodules="row.value"></submodulesStatus>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(server_info.query_result.serverSettings.zmqStatus)="row">
                <loaderPlaceholder :loading="!row.item.server_info._loading">
                    <zeroMQStatus :status="row.value"></zeroMQStatus>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(server_info.query_result.serverSettings.workers)="row">
                <loaderPlaceholder :loading="!row.item.server_info._loading">
                    <workersStatus :workers="row.value" :server_id="row.item.id"></workersStatus>
                </loaderPlaceholder>
            </template>

            <template v-slot:row-details="row">
                <RowDetails 
                    :details="row.item.server_info"
                    :server="row.item"
                    @actionRefresh="handleRefreshInfo({index: row.index, method: $event})"
                    @actionClose="toggleServerInfo(row.item, row.index, row)"
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
            :modalAction.sync="modalAddAction"
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
    </div>
</Layout>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import Layout from "@/components/layout/Layout.vue"
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"
import userPerms from "@/views/servers/elements/userPerms.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import proxyStatus from "@/views/servers/elements/proxyStatus.vue"
import workersStatus from "@/views/servers/elements/workersStatus.vue"
import submodulesStatus from "@/views/servers/elements/submodulesStatus.vue"
import zeroMQStatus from "@/views/servers/elements/zeroMQStatus.vue"
import connectionsSummary from "@/views/servers/elements/connectionsSummary.vue"
import contextualMenu from "@/components/ui/elements/contextualMenu.vue"
import RowDetails from "@/views/servers/elements/RowDetails.vue"
import DeleteModal from "@/views/servers/DeleteModal.vue"
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
        iconButton
    },
    data: function() {
        return {
            postInProgress: {
                modal: false,
            },
            refreshInProgress: false,
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
                        key: "status",
                        label: "Status",
                        sortable: true,
                        tdClass: "align-middle"
                    },
                    {
                        key: "server_info.query_result.serverUser.Role",
                        label: "User perms",
                        sortable: true,
                        class: "align-middle d-none d-xl-table-cell",
                    },
                    {
                        key: "server_info.query_result.connectedServers",
                        label: "Remote Connections",
                        sortable: true,
                        class: "align-middle d-none d-xl-table-cell",
                    },
                    {
                        key: "server_info.query_result.serverSettings.moduleStatus",
                        label: "Sub-modules",
                        sortable: true,
                        class: "align-middle d-none d-xxl-table-cell",
                    },
                    {
                        key: "server_info.query_result.serverSettings.proxyStatus",
                        label: "Proxy",
                        sortable: true,
                        class: "align-middle d-none d-xxl-table-cell",
                    },
                    {
                        key: "server_info.query_result.serverSettings.zmqStatus",
                        label: "ZeroMQ",
                        sortable: true,
                        class: "align-middle d-none d-xxl-table-cell",
                    },
                    {
                        key: "server_info.query_result.serverSettings.workers",
                        label: "Workers",
                        sortable: true,
                        class: "align-middle d-none d-md-table-cell",
                    },
                    //{
                    //    key: "auth_method",
                    //    sortable: false,
                    //    class: "d-none d-xl-table-cell text-nowrap",
                    //    formatter: (value) => {
                    //        return Array.isArray(value) ? value.join(", ") : ""
                    //    }
                    //},
                    {
                        key: "last_refresh",
                        sortable: true,
                        class: "align-middle py-0",
                        formatter: (value, key, item) => {
                            return item.server_info
                        }
                    },
                    {
                        key: "notification",
                        label: ""
                    }
                ],
            },
            tableItems: [],
            selectedServers: []
        }
    },
    computed: {
        ...mapState({
            getIndex: state => state.servers.all,
            githubVersion: state => state.servers.githubVersion,
            selectedServerGroup: state => state.serverGroups.selected,
        }),
        ...mapGetters({
            serverCount: "servers/serverCount"
        }),
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
            this.selectedServers = items
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
        genContextualMenu(index) {
            return [
                {
                    variant: "",
                    text: "Refresh",
                    icon: "sync-alt",
                    eventName: "handle-refresh-info",
                    callbackData: {index: index, method: "no_cache"}
                },
                {
                    variant: "",
                    text: "View connections",
                    icon: "network-wired",
                    eventName: "view-connections",
                    callbackData: {index: index}
                },
                {
                    variant: "",
                    text: "View network",
                    icon: "project-diagram",
                    eventName: "view-in-network",
                    callbackData: {index: index}
                },
                {
                    variant: "",
                    text: "Discover servers",
                    title: "Discover connected servers",
                    icon: "radar",
                    useAsset: true,
                    eventName: "handle-discover-servers-add",
                    callbackData: {index: index}
                },
                {
                    variant: "outline-primary",
                    disabled: !this.getIndex[index].canBeUpdated,
                    text: "Run updates",
                    icon: "arrow-up",
                    eventName: "run-updates",
                    callbackData: {index: index}
                },
                {
                    variant: "outline-danger",
                    text: "Delete server",
                    icon: "trash",
                    eventName: "open-deletion-modal",
                    callbackData: {index: index}
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
        toggleServerInfo(server, row_id) {
            this.$store.commit("servers/toggleShowDetails", row_id)
            if (server._showDetails) {
                this.refreshInfo(server, false)
            }
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
        refreshServerIndex() {
            this.refreshInProgress = true
            return new Promise((resolve, reject) => {
                this.$store.dispatch("servers/getAllServers")
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
                        this.refreshInProgress = false
                    })
            })
        },
        refreshSelected() {
            this.$store.dispatch("servers/refreshSelectedConnectionState", {selection: this.selectedServers})
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not reach Server",
                        variant: "danger",
                    })
                })
            this.$store.dispatch("servers/getSelectedInfo", {no_cache: true, selection: this.selectedServers})
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch server info",
                        variant: "danger",
                    })
                })
        },
        refreshAllServerOnlineStatus() {
            this.$store.dispatch("servers/refreshAllConnectionState")
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not reach Server",
                        variant: "danger",
                    })
                })
        },
        fullRefresh(quick=true) {
            if (quick) {
                this.refreshServerIndex()
                    .then(() => {
                        this.refreshAllServerOnlineStatus()
                        this.tableQuickRefresh()
                    })
            } else {
                this.refreshServerIndex()
                    .then(() => {
                        this.refreshAllServerOnlineStatus()
                        this.refreshAllInfo(true)
                    })
            }
        },
        fullRefreshIfNeeded() {
            if (this.getIndex.length === 0) {
                this.fullRefresh()
            }
        },
        tableQuickRefresh() {
            if (this.$refs.serverTable !== undefined) {
                this.$refs.serverTable.refresh()
            }
        },
        handleRefreshInfo(data) {
            const index = data.index
            const method = data.method
            let server = this.getIndex[index]
            this.$store.dispatch("servers/refreshConnectionState", server)
            this.refreshInfo(server, method == "no_cache")
        },
        refreshInfo(server, no_cache=false) {
            this.$store.dispatch("servers/getInfo", {server: server, no_cache: no_cache})
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch server info",
                        variant: "danger",
                    })
                })
        },
        refreshAllInfo(no_cache=false) {
            this.$store.dispatch("servers/getAllInfo", {no_cache: no_cache})
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch server info",
                        variant: "danger",
                    })
                })
        },
    },
    watch: {
        refreshInProgress: function() {
            this.table.timeKey += 1 // used to force reload of the timeSinceLastRefresh component
        },
        selectedServerGroup: function() {
            this.fullRefresh()
        }
    },
    mounted() {
        this.fullRefreshIfNeeded()
        this.fetchGithubVersionIfNeeded()
    },
}
</script>

<style>
.table-primary-background {
    background-color: #b8daff;
}
</style>
