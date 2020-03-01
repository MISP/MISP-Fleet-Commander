<template>
<Layout name="LayoutDefault">
    <div>
        <h3>
            <iconForScope scope="servers"></iconForScope>
            MISP Servers
        </h3>
        
        <div class="mb-3">
            <b-button
                size="sm"
                variant="success"
                v-b-modal.modal-add
            >
                <b-icon icon="plus"></b-icon>Add Server
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
            striped outlined hover show-empty small
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
                        :server_id="row.item.id"
                    ></userPerms>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(last_refresh)="row">
                <loaderPlaceholder :loading="!row.value._loading">
                    <timeSinceRefresh
                        :timestamp="row.value.timestamp"
                    ></timeSinceRefresh>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(server_info.query_result.connectedServers)="row">
                <loaderPlaceholder :loading="!row.item.server_info._loading">
                    <connectionsSummary
                        v-if="typeof row.value !== 'string'"
                        :connections="row.value"
                        :server_id="row.item.id"
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

            <template v-slot:cell(actions)="row">
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
                    <b-button :id="`popover-row-option-${row.index}`" href="#" class="ml-1" size="xs" variant="link">
                        <i class="fas fa-ellipsis-v"></i>
                    </b-button>
                     <b-popover
                        :ref="`popoverRow${row.index}`"
                        :target="`popover-row-option-${row.index}`"
                        placement="bottomleft"
                        triggers="focus"
                    >
                        <b-button 
                            size="sm" variant="primary" class="d-flex align-items-center w-100 mb-1"
                            @click="closePopover(row.index, handleRefreshInfo(row.item, 'no_cache'))"
                        >
                            <b-icon icon="arrow-clockwise" class="mr-1"></b-icon>
                            <span class="w-100">Refresh</span>
                        </b-button>
                        <b-button
                            size="sm" variant="primary" class="d-flex align-items-center w-100 mb-1"
                            @click="viewConnections(row.item)"
                        >
                            <i class="mr-1 fas fa-network-wired"></i>
                            <span class="w-100">View connections</span>
                        </b-button>
                        <b-button
                            size="sm" variant="danger" class="d-flex align-items-center w-100"
                            @click="openDeletionModal(row.item)"
                        >
                            <b-icon icon="trash-fill" class="mr-1"></b-icon>
                            <span class="w-100">Delete server</span>
                        </b-button>
                    </b-popover>
                </div>
            </template>

            <template v-slot:row-details="row">
                <RowDetails 
                    :details="row.item.server_info"
                    :server="row.item"
                    @actionRefresh="handleRefreshInfo(row.item, $event)"
                ></RowDetails>
            </template>

            <template v-slot:table-caption>Showing {{ table.totalRows }} out of {{ serverCount }} Servers</template>
        </b-table>

        <DeleteModal
            :serverToDelete="serverToDelete"
            @actionDelete="handleDelete"
        ></DeleteModal>

        <AddModal
            :modalAction="modalAddAction"
            :serverForm="serverToEdit.formData"
            @actionAdd="handleAdd"
        ></AddModal>

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
import RowDetails from "@/views/servers/RowDetails.vue"
import DeleteModal from "@/views/servers/DeleteModal.vue"
import AddModal from "@/views/servers/AddModal.vue"


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
        workersStatus,
        RowDetails,
        DeleteModal,
        AddModal
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
            table: {
                isBusy: false,
                filtered: "",
                totalRows: 0,
                currentPage: 1,
                perPage: 30,
                serverStatus: {},
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
                        key: "authkey",
                        sortable: false,
                        class: "d-none d-xl-table-cell",
                        formatter: value => {
                            return value.slice(0, 4) + " … " + value.slice(36, 40)
                        }
                    },
                    {
                        key: "last_refresh",
                        sortable: true,
                        class: "align-middle",
                        formatter: (value, key, item) => {
                            return item.server_info
                        }
                    },
                    {
                        key: "actions",
                        class: "align-middle d-none d-md-table-cell",
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
    },
    methods: {
        onFiltered(filteredItems) {
            this.table.totalRows = filteredItems.length
            this.table.currentPage = 1
        },
        onSorted() {
            this.table.currentPage = 1
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
        openEditModal(server) {
            this.serverToEdit.formData = JSON.parse(JSON.stringify(server)) // deep clone
            this.modalAddAction = "Edit"
            this.$bvModal.show("modal-add")
        },
        openDeletionModal(server) {
            this.$bvModal.show("modal-delete")
            this.serverToDelete = server
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
        handleRefreshInfo(server, event) {
            this.$store.dispatch("servers/refreshConnectionState", server)
            this.refreshInfo(server, event == "no_cache")
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
    mounted () {
        this.fullRefresh()
    }
}
</script>

<style scoped>
</style>
