<template>
<Layout name="LayoutDefault">
    <div>
        <h3>
            <iconForScope scope="servers"></iconForScope>
            Servers
        </h3>
        
        <div class="mb-3">
            <b-button
                size="sm"
                variant="success"
                v-b-modal.modal-add
            >
                <i class="fas fa-plus mr-1"></i>Add Server
            </b-button>
            <b-button
                size="sm"
                variant="success"
                class="ml-1"
                v-b-modal.modal-batch-add
            >
                <i class="fas fa-plus mr-1"></i>Batch Add Server
                <sup class="ml-1"><b-badge pill variant="light">Experimental</b-badge></sup>
            </b-button>
        </div>
        <div class="d-flex justify-content-between">
            <div>
                <b-pagination
                    v-model="table.currentPage"
                    v-if="table.totalRows > table.perPage"
                    :per-page="table.perPage"
                    :total-rows="table.totalRows"
                    aria-controls="server-table"
                ></b-pagination>
            </div>
            <div class="align-items-center d-flex w-25">
                <b-input-group size="sm">
                    <b-form-input
                        v-model="table.filter"
                        type="search"
                        id="filterInput"
                        placeholder="Type to Search"
                        class="border-bottom-0 rounded-top align-self-end"
                        style="border-radius: 0"
                    ></b-form-input>
                </b-input-group>
                <b-button class="ml-2" variant="primary" size="sm" @click="fullRefresh()">
                    <b-icon icon="arrow-clockwise" :class="{'fa-spin': refreshInProgress}" title="Refresh Servers"></b-icon>
                </b-button>
           </div>
        </div>
        <b-table 
            striped outlined show-empty small
            table-class="table-auto-hide-action"
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
        >
            <template v-slot:table-busy>
                <div class="text-center text-danger my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong class="ml-2">Loading...</strong>
                </div>
            </template>

            <template v-slot:cell(url)="row">
                <b-link :href="row.value" target="_blank">{{ row.value }} <sup class="fa fa-external-link-alt"></sup></b-link>
            </template>

            <template v-slot:cell(status)="row">
                <loaderPlaceholder :loading="!row.value._loading">
                    <span
                        :class="['text-nowrap', row.value.error ? 'text-danger' : 'text-success']"
                    >
                        <b-icon icon="circle-fill"></b-icon>
                        {{ row.value.data }}
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
                                <b-icon class="text-secondary" :icon="row.detailsShowing ? 'arrows-collapse' : 'arrows-expand'"></b-icon>
                            </b-button>
                            <b-button class="ml-1" size="xs" variant="link" @click="openEditModal(row.item)">
                                <i class="fas fa-edit"></i>
                            </b-button>
                            <b-button :id="`popover-row-option-${row.index}`" href="#" class="ml-1" size="xs" variant="link" @click="forceHidden(row.index)">
                                <i class="fas fa-ellipsis-v"></i>
                            </b-button>
                            <b-popover
                                :ref="`popoverRow${row.index}`"
                                :target="`popover-row-option-${row.index}`"
                                placement="bottomleft"
                                triggers="focus"
                                custom-class="popover-no-body"
                                @hidden="clearForcedHidden"
                            >
                                <contextualMenu
                                    :menu="genContextualMenu(row.index)"
                                    @handle-refresh-info="handleRefreshInfo"
                                    @view-connections="viewConnections"
                                    @view-in-network="viewInNetwork"
                                    @open-deletion-modal="openDeletionModal"
                                ></contextualMenu>
                            </b-popover>
                        </div>
                    </span>
                </span>
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
                ></RowDetails>
            </template>

            <template v-slot:table-caption>Showing {{ table.totalRows }} out of {{ serverCount }} Servers</template>
        </b-table>

        <DeleteModal
            :serverToDelete="serverToDelete"
            @actionDelete="handleDelete"
        ></DeleteModal>

        <AddModal
            :modalAction.sync="modalAddAction"
            :serverForm="validServerToEdit"
            @actionAdd="handleAdd"
        ></AddModal>

        <BatchAddModal
            @actionAdd="handleBatchAdd"
        ></BatchAddModal>
    </div>
</Layout>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import Layout from "@/components/layout/Layout.vue"
import iconForScope from "@/components/ui/elements/iconForScope.vue"
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"
import userPerms from "@/components/ui/elements/userPerms.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import proxyStatus from "@/components/ui/elements/proxyStatus.vue"
import workersStatus from "@/components/ui/elements/workersStatus.vue"
import submodulesStatus from "@/components/ui/elements/submodulesStatus.vue"
import zeroMQStatus from "@/components/ui/elements/zeroMQStatus.vue"
import connectionsSummary from "@/components/ui/elements/connectionsSummary.vue"
import contextualMenu from "@/components/ui/elements/contextualMenu.vue"
import RowDetails from "@/views/servers/RowDetails.vue"
import DeleteModal from "@/views/servers/DeleteModal.vue"
import AddModal from "@/views/servers/AddModal.vue"
import BatchAddModal from "@/views/servers/BatchAddModal.vue"


export default {
    name: "TheServers",
    components: {
        Layout,
        iconForScope,
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
        BatchAddModal
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
            forcedHidden: -1,
            table: {
                isBusy: false,
                filtered: "",
                totalRows: 0,
                currentPage: 1,
                perPage: 30,
                filterFields: ["name", "url"],
                fields: [
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
                    {
                        key: "auth_method",
                        sortable: false,
                        class: "d-none d-xl-table-cell text-nowrap",
                        formatter: (value) => {
                            return Array.isArray(value) ? value.join(", ") : ""
                        }
                    },
                    {
                        key: "last_refresh",
                        sortable: true,
                        class: "align-middle py-0",
                        formatter: (value, key, item) => {
                            return item.server_info
                        }
                    }
                ],
            },
            tableItems: [],
        }
    },
    computed: {
        ...mapState({
            getIndex: state => state.servers.all
        }),
        ...mapGetters({
            serverCount: "servers/serverCount"
        }),
        validServerToEdit() {
            return this.serverToEdit.formData
        }
    },
    methods: {
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
                    variant: "outline-danger",
                    text: "Delete server",
                    icon: "trash",
                    eventName: "open-deletion-modal",
                    callbackData: {index: index}
                },
            ]
        },
        toggleServerInfo(server, row_id, row) {
            this.$store.commit("servers/toggleShowDetails", row_id)
            if (server._showDetails) {
                row.item._rowVariant = "primary"
                this.refreshInfo(server, false)
            } else {
                row.item._rowVariant = ""
            }
        },
        forceHidden(row_id) {
            this.forcedHidden = row_id
        },
        clearForcedHidden() {
            this.forcedHidden = -1
        },
        closePopover(row_id) {
            this.$refs[`popoverRow${row_id}`].$emit("close")
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
        viewConnections(data) {
            return data
        },
        viewInNetwork(data) {
            return data
        },
        refreshServerIndex(callback) {
            this.refreshInProgress = true
            this.$store.dispatch("servers/getAllServers")
                .then(() => {
                    this.table.totalRows = this.serverCount
                    callback()
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch server index",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.refreshInProgress = false
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
        fullRefresh() {
            this.refreshServerIndex(
                this.refreshAllServerOnlineStatus
            )
        },
        handleRefreshInfo(data) {
            const index = data.index
            const method = data.method
            this.closePopover(index)
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
        }
    },
    mounted() {
        this.fullRefresh()
    }
}
</script>

<style scoped>
</style>
