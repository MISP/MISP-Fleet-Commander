<template>
<Layout name="LayoutDefault">
    <div class="page-container">
        <div class="d-flex justify-content-between">
            <div class="d-flex" style="margin-top: -5px">
                <div class="text-nowrap mr-2 pb-1">
                    <b-button
                        size="sm"
                        variant="primary"
                        v-b-modal.modal-add
                    >
                        <i class="fas fa-plus"></i> Add Commander
                    </b-button>
                </div>
                <b-pagination
                    class="mb-0"
                    v-model="table.currentPage"
                    size="sm"
                    :per-page="table.perPage"
                    :total-rows="table.totalRows"
                    aria-controls="server-table"
                ></b-pagination>
            </div>
            <div class="w-25">
                <b-button-toolbar class="justify-content-end flex-nowrap">
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
                    <b-button class="ml-2" variant="primary" size="sm" @click="refreshUsers()">
                        <i :class="{'fas fa-sync-alt': true, 'fa-spin': refreshInProgress}" title="Refresh Connections"></i>
                    </b-button>
                </b-button-toolbar>
           </div>
        </div>

        <b-table 
            striped outlined show-empty
            responsive="md"
            id="users-table"
            ref="userTable"
            :per-page="table.perPage"
            :current-page="table.currentPage"
            :busy.sync="table.isBusy"
            :items="userList" 
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

            <template v-slot:cell(user_settings)="row">
                <div class="d-flex flex-column">
                    <b-button
                        @click="openUserSettingModal(row.item)"
                        variant="primary"
                        size="xs"
                    >Edit user settings</b-button>
                    <span class="text-muted text-center" style="font-size: 0.66rem;">{{ Object.keys(row.value).length }} settings set</span>
                </div>
            </template>

            <template v-slot:cell(apikey)="row">
                <span
                    @click="(e) => e.target.classList.toggle('blurred')"
                    class="blurred"
                >{{ row.value }}</span>
            </template>

            <template v-slot:cell(action)="row">
                <span class="d-block" style="width: 90px;">
                    <b-button-group size="sm">
                        <b-button
                            variant="primary"
                            @click="openEditModal(row.item.id)"
                        >
                            <i class="fas fa-edit"></i>
                        </b-button>
                        <b-button
                            variant="danger"
                            @click="openDeleteModal(row.item.id)"
                        >
                            <i class="fas fa-trash"></i>
                        </b-button>
                        <b-button
                            title="Resfresh API Key"
                            variant="primary"
                            @click="openAPIKeyModal(row.item.id)"
                        >
                            <i class="fas fa-key"></i>
                        </b-button>
                    </b-button-group>
                </span>
            </template>

            <template v-slot:table-caption>Showing {{ table.totalRows }} out of {{ userCount }} users</template>
        </b-table>

        <AddModal
            :modalAction.sync="modalAddAction"
            :userForm="validUserToEdit"
            @addition-success="handleAdd"
       ></AddModal>
        <DeleteModal
            :userToDelete="validUserToDelete"
            @deletion-success="handleDelete"
       ></DeleteModal>
        <APIKeyModal
            :userIDToGenAPIKey="userIDToGenAPIKey"
            @deletion-success="handleDelete"
       ></APIKeyModal>
        <UserSettingSaveModal
            :selectedUser="selectedUser"
            @save-success="handleSaveSettings"
        ></UserSettingSaveModal>
    </div>
</Layout>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import Layout from "@/components/layout/Layout.vue"
import AddModal from "@/views/users/AddModal.vue"
import DeleteModal from "@/views/users/DeleteModal.vue"
import APIKeyModal from "@/views/users/APIKeyModal.vue"
import UserSettingSaveModal from "@/views/users/UserSettingSaveModal.vue"
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"
import formInputFromConfig from "@/components/ui/elements/formInputFromConfig.vue"

export default {
    name: "UserIndex",
    components: {
        Layout,
        AddModal,
        DeleteModal,
        APIKeyModal,
        UserSettingSaveModal,
        jsonViewer,
        formInputFromConfig,
    },
    data: function () {
        return {
            refreshInProgress: false,
            modalAddAction: "Add",
            userToEdit: { formData: {} },
            userToDelete: { formData: {} },
            userIDToGenAPIKey: false,
            table: {
                isBusy: false,
                filtered: "",
                totalRows: 0,
                currentPage: 1,
                perPage: 30,
                filterFields: ["email",],
                fields: [
                    {
                        key: "email",
                        sortable: true
                    },
                    {
                        key: "created",
                        sortable: true,
                    },
                    {
                        key: "updated",
                        sortable: true,
                    },
                    {
                        key: "apikey",
                        sortable: false,
                    },
                    {
                        key: "user_settings",
                        sortable: false,
                    },
                    {
                        key: "action",
                        sortable: false,
                    }
                ]
            },
            selectedUser: {},
            input_valid_type: ['text', 'password', 'email', 'number', 'url', 'tel', 'search', 'date', 'datetime', 'datetime-local', 'month', 'week', 'time', 'range', 'color']
        }
    },
    computed: {
        ...mapState({
            getUsers: state => state.users.all
        }),
        ...mapGetters({
            userCount: "users/userCount",
            userList: "users/getUserList",
        }),
        validUserToEdit() {
            return this.userToEdit.formData
        },
        validUserToDelete() {
            return this.userToDelete.formData
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
        refreshUsers() {
            this.refreshInProgress = true
            this.$store.dispatch("users/getUsers")
                .then(() => {
                    this.table.totalRows = this.userCount
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch user index",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.refreshInProgress = false
                })
        },
        fetchAllUserSettings() {
            this.refreshInProgress = true
            this.$store.dispatch("userSettings/getSettingConfig")
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch all user settings",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.refreshInProgress = false
                })
        },
        resetModalAction() {
            this.modalAddAction = "Add"
        },
        openEditModal(user_id) {
            const user = this.userList.filter(u => u.id == user_id)[0]
            this.userToEdit.formData = JSON.parse(JSON.stringify(user)) // deep clone
            this.modalAddAction = "Edit"
            this.$bvModal.show("modal-add")
        },
        openAPIKeyModal(user_id) {
            this.userIDToGenAPIKey = user_id
            this.$bvModal.show("modal-gen-apikey")
        },
        openDeleteModal(user_id) {
            const user = this.userList.filter(u => u.id == user_id)[0]
            this.userToDelete.formData = JSON.parse(JSON.stringify(user)) // deep clone
            this.$bvModal.show("modal-delete")
        },
        handleAdd() {
            this.refreshUsers()
        },
        handleEdit() {
            this.userToEdit.formData = {}
            this.refreshUsers()
        },
        handleDelete() {
            this.userToDelete.formData = {}
            this.refreshUsers()
        },
        handleSaveSettings() {
            this.refreshUsers()
        },
        openUserSettingModal(user) {
            this.selectedUser = user
            this.$bvModal.show("user-setting-modal")
        },
    },
    mounted() {
        this.refreshUsers()
        this.fetchAllUserSettings()
    }
}
</script>

<style>
.apikey {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: .85em;
}
.blurred {
    filter: blur(5px);
}
</style>
