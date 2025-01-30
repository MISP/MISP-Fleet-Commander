<template>
    <div>
        <h6 class="card-header px-2 py-1">
            <div class="d-flex">
                <span class="my-auto">Notifications Board</span>
                <b-button
                    class="ml-auto"
                    variant="primary"
                    size="sm"
                    title="Quick refresh"
                    @click="quickRefresh()"
                >
                    <i :class="{'fas fa-sync-alt': true, 'fa-spin': refreshInProgress}" title="Refresh Servers"></i>
                </b-button>
            </div>
        </h6>
        <div class="p-1">
            <b-tabs card v-if="notificationPlugins.length > 0">
                <b-tab
                    v-for="plugin in notificationPlugins"
                    v-bind:key="plugin.id"
                    :title="plugin.name"
                    lazy no-body
                    style="height: 500px; overflow: scroll; resize: vertical;"
                >
                    <div class="d-flex mt-1">
                        <div>
                            <b-pagination
                                class="mb-0"
                                v-model="table.currentPage"
                                size="sm"
                                :per-page="table.perPage"
                                :total-rows="table.totalRows"
                                aria-controls="server-table"
                            ></b-pagination>
                        </div>
                        <div class="w-50 ml-auto">
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
                            </b-button-toolbar>
                        </div>
                    </div>
                    <b-table 
                        show-empty small
                        tbody-tr-class="no-outline"
                        thead-tr-class="no-bgcolor"
                        id="notification-table"
                        ref="notificationTable"
                        class="mb-0"
                        :busy.sync="refreshInProgress"
                        :items="pluginNotificationFor(server.id, plugin.id).data" 
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

                        <template v-slot:cell(timestamp)="row">
                            {{ row.value | moment('MMMM Do YYYY, HH:mm:ss') }}
                        </template>

                        <template v-slot:cell(severity)="row">
                            <b-badge :variant="severity_to_color(row.value)" style="transition: unset;">
                                {{ row.value | severity_to_text }}
                            </b-badge>
                        </template>

                        <template v-slot:cell(data)="row">
                            <b-button :id="`popover-${row.index}`" variant="primary" size="xs">View</b-button>
                            <b-popover :target="`popover-${row.index}`" triggers="click" placement="bottomleft" boundary="viewport">
                                <jsonViewer
                                    :item="row.value"
                                    :open="true"
                                ></jsonViewer>
                            </b-popover>
                        </template>

                        <template v-slot:cell(action)="">
                            <b-button class="ml-1" size="xs" variant="light" title="Accept" disabled>
                                <i class="fas fa-check"></i>
                            </b-button>
                            <b-button class="ml-1" size="xs" variant="light" disabled>
                                <i class="fas fa-cogs"></i>
                            </b-button>
                            <b-button class="ml-1" size="xs" variant="outline-danger" title="Delete notification" disabled>
                                <i class="fas fa-trash"></i>
                            </b-button>
                        </template>

                        <template v-slot:table-caption>Showing {{ table.totalRows }} out of {{ pluginNotificationFor(server.id, plugin.id).data.length }}</template>
                    </b-table>
                </b-tab>
            </b-tabs>
            <div v-else class="p-3 text-center">
                <span class="text-muted">No notifications</span>
            </div>
        </div>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"

export default {
    name: "ServerNotifications",
    components: {
        jsonViewer
    },
    props: {
        server: {
            required: true,
            type: Object
        }
    },
    computed: {
        ...mapState({
            notifications: state => state.plugins.pluginNotifications
        }),
        ...mapGetters({
            notificationPlugins: "plugins/notificationPlugins",
            pluginNotificationFor: "plugins/pluginNotificationFor",
        }),
    },
    data: function () {
        return {
            refreshInProgress: false,
            table: {
                filtered: "",
                totalRows: 0,
                currentPage: 1,
                perPage: 30,
                filterFields: [""],
                fields: [
                    {
                        key: "timestamp",
                        label: "Date",
                        sortable: true,
                        tdClass: "text-nowrap"
                    },
                    {
                        key: "origin",
                        label: "Origin",
                        sortable: true
                    },
                    {
                        key: "severity",
                        label: "Severity",
                        sortable: true
                    },
                    {
                        key: "title",
                        label: "Title",
                        sortable: true,
                    },
                    {
                        key: "data",
                        label: "Data",
                        tdClass: "text-nowrap"
                    },
                    {
                        key: "action",
                        label: "Action",
                        tdClass: "text-nowrap"
                    },
                ],
            },
        }
    },
    filters: {
        severity_to_text: (severity_level) => {
            if (severity_level == 1) {
                return "Low"
            } else if (severity_level == 2) {
                return "Medium"
            } else if (severity_level == 3) {
                return "High"
            } else {
                return "N/A"
            }
        }
    },
    methods: {
        severity_to_color: (severity_level) => {
            if (severity_level == 1) {
                return "primary"
            } else if (severity_level == 2) {
                return "warning"
            } else if (severity_level == 3) {
                return "danger"
            } else {
                return "secondary"
            }
        },
        refreshNotifications() {
            this.refreshInProgress = true
            return new Promise((resolve, reject) => {
                this.$store.dispatch("plugins/fetchNotifications", {serverID: this.server.id})
                     .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        this.$bvToast.toast(error, {
                            title: "Could not fetch server notifications",
                            variant: "danger",
                        })
                        reject()
                    })
                    .finally(() => {
                        this.refreshInProgress = false
                    })
            })
        },
        quickRefresh() {
            this.refreshNotifications()
        },
        onFiltered(filteredItems) {
            this.table.totalRows = filteredItems.length
            this.table.currentPage = 1
        },
        onSorted() {
            this.table.currentPage = 1
        },
    },
    mounted() {
        this.refreshNotifications()
    }
}
</script>

<style scoped>
thead tr th {
    border-top: 0;
}
</style>
