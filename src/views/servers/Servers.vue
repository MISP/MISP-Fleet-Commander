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
                <span
                    v-if="Object.keys(row.value).length != 0"
                    :class="['text-nowrap', row.value.error ? 'text-danger' : 'text-success']"
                >
                    <b-icon icon="circle-fill"></b-icon>
                    {{ row.value.data }}
                </span>
                <cellLoading v-else :width="'70px'"></cellLoading>
            </template>

            <template v-slot:cell(actions)="row">
                <div class="btn-group">
                    <b-button
                        size="xs" variant ="link"
                        @click="toggleDiagnostic(row.item, row.index, row)"
                    >
                        <b-icon class="text-secondary" :icon="row.detailsShowing ? 'arrows-collapse' : 'arrows-expand'"></b-icon>
                    </b-button>
                    <b-button class="ml-1" size="xs" variant="link" @click="openEditModal(row.item)">
                        <i class="fas fa-edit"></i>
                    </b-button>
                    <b-button class="ml-1" size="xs" variant="link" @click="openDeletionModal(row.item)">
                        <b-icon icon="trash-fill" class="text-danger"></b-icon>
                    </b-button>
                </div>
            </template>

            <template v-slot:row-details="{ item }">
                <RowDetails 
                    :details="item.diagnostic"
                    :server="item"
                    @actionRefresh="refreshDiagnostic(item)"
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
import axios from "axios"
import Layout from "@/components/layout/Layout.vue"
import iconForScope from "@/components/ui/elements/iconForScope.vue"
import cellLoading from "@/components/ui/elements/cellLoading.vue"
import RowDetails from "@/views/servers/RowDetails.vue"
import DeleteModal from "@/views/servers/DeleteModal.vue"
import AddModal from "@/views/servers/AddModal.vue"


export default {
    name: "TheServers",
    components: {
        Layout,
        iconForScope,
        cellLoading,
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
                        key: "user",
                        label: "User",
                        sortable: true,
                        class: "d-none d-xl-table-cell",
                    },
                    {
                        key: "submoduleStatus",
                        label: "Sub-modules",
                        sortable: true,
                        class: "d-none d-xl-table-cell",
                    },
                    {
                        key: "proxy",
                        sortable: true,
                        class: "d-none d-xxl-table-cell",
                    },
                    {
                        key: "zeromq",
                        label: "ZeroMQ",
                        sortable: true,
                        class: "d-none d-xxl-table-cell",
                    },
                    {
                        key: "workers",
                        sortable: true,
                        class: "d-none d-md-table-cell",
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
                        key: "lastRefresh",
                        sortable: true,
                    },
                    {
                        key: "actions",
                        class: "d-none d-md-table-cell",
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
        toggleDiagnostic(server, row_id, row) {
            this.$store.commit("servers/toggleShowDetails", row_id)
            if (server._showDetails) {
                row.item._rowVariant = "primary"
                this.queryDiagnostic(server, row_id)
            } else {
                row.item._rowVariant = ""
            }
        },
        handleDelete() {
            this.serverToDelete = {}
            this.$refs.serverTable.refresh()
        },
        handleAdd() {
            this.$refs.serverTable.refresh()
        },
        queryDiagnostic(server) {
            this.$store.dispatch("servers/getDiagnostic", server)
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
                    this.$bvToast.toast(error.toJSON(), {
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
        refreshDiagnostic(server) {
            this.$store.dispatch("servers/getDiagnostic", server)
        }
    },
    created () {
        this.fullRefresh()
    }
}
</script>

<style scoped>
</style>
