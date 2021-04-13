<template>
<div>
    <div class="mb-2">
        <b-button
            size="sm"
            variant="primary"
            title="Not sure if this will be added. TBD"
            disabled
        >
            <i class="fas fa-plus"></i> Add user
        </b-button>
    </div>
    <div class="d-flex justify-content-between">
        <div class="d-flex" style="margin-top: -5px">
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
        <div class="w-50">
            <b-button-toolbar class="justify-content-end flex-nowrap">
                <b-input-group size="sm" class="px-0 col" style="min-width: 150px;">
                    <b-form-input
                        v-model="table.filter"
                        type="search"
                        id="filterInput"
                        placeholder="Type to Search"
                        class="border-bottom-0 rounded-top align-self-end"
                        style="border-radius: 0"
                    ></b-form-input>
                </b-input-group>
                <b-button
                    class="ml-2"
                    variant="primary"
                    size="sm"
                    title="Quick refresh users"
                    @click="loadUsers()"
                >
                    <i :class="['fas fa-sync-alt', {'fa-spin': table.isBusy}]" title="Quick refresh users"></i>
                </b-button>
            </b-button-toolbar>
        </div>
    </div>

    <b-table 
        outlined show-empty small
        table-class="table-auto-hide-action"
        table-variant="none"
        selected-variant="table-none"
        tbody-tr-class="no-outline"
        thead-tr-class="no-bgcolor"
        responsive="md"
        id="user-table"
        ref="userTable"
        :per-page="table.perPage"
        :current-page="table.currentPage"
        :busy.sync="table.isBusy"
        :items="users" 
        :fields="table.fields"
        :filterIncludedFields="table.filterFields"
        :filter="table.filter"
        :no-provider-paging="true"
        :no-provider-sorting="true"
        :no-provider-filtering="true"
        :sort-icon-left="true"
        @filtered="onFiltered"
        @sort-changed="onSorted"
        @row-clicked="rowClickHandler"
    >
            <template v-slot:table-busy>
                <div class="text-center text-danger my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong class="ml-2">Loading...</strong>
                </div>
            </template>

            <template v-slot:cell(Role)="row">
                <userPerms
                    :perms="row.value"
                    :row_id="row.index"
                    context="userindex"
                ></userPerms>
            </template>

            <template v-slot:cell(User.date_created)="row">
                <timeSinceRefresh
                    :timestamp="row.value"
                    type="ddd DD/MM/YYYY HH:mm"
                    :noicon="true"
                    :noformat="true"
                ></timeSinceRefresh>
            </template>

            <template v-slot:cell(User.date_modified)="row">
                <timeSinceRefresh
                    :timestamp="row.value"
                    :noicon="true"
                    :noformat="true"
                ></timeSinceRefresh>
            </template>

            <template v-slot:cell(User.last_login)="row">
                <timeSinceRefresh
                    :timestamp="row.value"
                    :noicon="true"
                    :noformat="true"
                ></timeSinceRefresh>
            </template>

            <template v-slot:cell(User.disabled)="row">
                <b-badge pill :variant="row.value ? 'danger' : 'success' ">
                    {{ row.value ? 'Disabled' : 'Enabled' }}
                </b-badge>
            </template>
    </b-table>

    <UserAdministrationModal
        v-if="selectedItem !== null"
        ref="modal-user-administration"
        :user="selectedItem"
        :server="getServer"
    ></UserAdministrationModal>
</div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import UserAdministrationModal from "@/views/servers/elements/mispRemoteAdministration/UserAdministrationModal.vue"
import userPerms from "@/views/servers/elements/userPerms.vue"

export default {
    name: "userAdministration",
    components: {
        timeSinceRefresh,
        UserAdministrationModal,
        userPerms
    },
    props: {
        server: {
            type: Object,
            required: true
        }
    },
    data: function() {
        return {
            table: {
                isBusy: false,
                filtered: "",
                totalRows: 0,
                currentPage: 1,
                perPage: 30,
                optionsPerPage: [{ text: 30, value: 30 }, { text: 50, value: 50 }, { text: 100, value: 100 }],
                filterFields: ["email"],
                fields: [
                    {
                        key: "User.email",
                        label: "Email",
                        sortable: true
                    },
                    {
                        key: "Organisation.name",
                        label: "Org. Name",
                        sortable: true
                    },
                    {
                        key: "Role",
                        label: "User perms",
                        sortable: true,
                    },
                    {
                        key: "User.date_created",
                        label: "Created",
                        sortable: true
                    },
                    {
                        key: "User.date_modified",
                        label: "Last modified",
                        sortable: true
                    },
                    {
                        key: "User.last_login",
                        label: "Last login",
                        sortable: true
                    },
                    {
                        key: "User.disabled",
                        label: "State",
                        sortable: true
                    },
                ],
            },
            users: [],
            selectedItem: null
        }
    },
    computed: {
        ...mapGetters({
            getServerById: "servers/getServerById"
        }),
        getServer: function() {
            return this.getServerById(this.server.id)
        },
    },
    methods: {
        onFiltered(filteredItems) {
            this.table.totalRows = filteredItems.length
            this.table.currentPage = 1
        },
        onSorted() {
            this.table.currentPage = 1
        },
        rowClickHandler(item) {
            this.selectedItem = item
            this.$nextTick(() => {
                this.$bvModal.show("modal-user-administration")
            })
        },
        getUsers: function() {
            return this.getServer.server_data.users
        },
        loadUsers() {
            this.table.isBusy = true
            this.$store.dispatch("servers/getUsers", this.server.id)
                .then(() => {
                    this.table.isBusy = false
                    this.users = this.getUsers()
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch server info",
                        variant: "danger",
                    })
                })
        }
    },
    created() {
        this.loadUsers()
    }
}
</script>

<style scoped>
</style>