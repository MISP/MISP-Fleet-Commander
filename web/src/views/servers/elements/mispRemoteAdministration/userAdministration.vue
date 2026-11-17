<template>
<div>
    <div class="mb-2">
        <b-button
            size="sm"
            variant="primary"
            v-b-modal="'modal-administration-user-add'"
        >
            <i class="fas fa-plus"></i> Add user
        </b-button>
    </div>
    <div v-if="orgFilter" class="org-filter" role="status">
        <i class="fas fa-building" aria-hidden="true"></i>
        <span>Users of <strong>{{ orgFilter.name }}</strong> · {{ shownUsers.length }}</span>
        <button type="button" class="btn btn-link org-filter-clear" title="Show every user" aria-label="Show every user" @click="$emit('clear-org-filter')">
            <i class="fas fa-times" aria-hidden="true"></i>
        </button>
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
        :items="shownUsers"
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

    <UserAdd
        :users="users"
        :server="getServer"
        @user-added="loadUsers"
    ></UserAdd>

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
import UserAdd from "@/views/servers/elements/mispRemoteAdministration/userAdministrationActions/userAdd.vue"
import userPerms from "@/views/servers/elements/userPerms.vue"

export default {
    name: "userAdministration",
    components: {
        timeSinceRefresh,
        UserAdministrationModal,
        UserAdd,
        userPerms
    },
    props: {
        server: {
            type: Object,
            required: true
        },
        // {id, name}: only the users of that organisation
        orgFilter: {
            type: Object,
            default: null
        },
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
                filter: null,
                filterFields: ["email", "orgname"],
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
                        label: "Disabled State",
                        sortable: true
                    },
                ],
            },
            users: [],
            selectedItem: null
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers,
            server_users: state => state.servers.server_users,
        }),
        getServerId: function() {
            return this.server.id
        },
        getServer: function() {
            return this.server
        },
        getServerUsers: function() {
            return this.server_users[this.getServerId]
        },
        shownUsers: function() {
            if (!this.orgFilter) {
                return this.users
            }
            return this.users.filter(user => user.Organisation && Number(user.Organisation.id) === Number(this.orgFilter.id))
        },
    },
    watch: {
        shownUsers: function(users) {
            this.table.totalRows = users.length
            this.table.currentPage = 1
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
        loadUsers() {
            this.table.isBusy = true
            this.$store.dispatch("servers/getUsers", this.server.id)
                .then(() => {
                    this.users = (this.getServerUsers || [])
                        .filter(user => user && user.User)
                        .map(user => Object.assign({}, user, { // needed for b-table filters
                            email: user.User.email,
                            orgname: user.Organisation ? user.Organisation.name : "",
                        }))
                })
                .catch(error => {
                    this.$bvToast.toast(typeof error === "string" ? error : (error && error.message) || "Something went wrong", {
                        title: "Could not fetch the users",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.table.isBusy = false
                })
        }
    },
    created() {
        this.loadUsers()
    }
}
</script>

<style scoped>
.org-filter {
    display: inline-flex;
    align-items: center;
    gap: 0.45em;
    margin-bottom: 0.6rem;
    padding: 0.2rem 0.3rem 0.2rem 0.7rem;
    border: 1px solid #b8d4e6;
    border-radius: 1rem;
    background: #eaf3f8;
    color: #1f4a66;
    font-size: 0.85rem;
}

.org-filter-clear {
    padding: 0 0.4rem;
    color: inherit;
    line-height: 1;
}
</style>