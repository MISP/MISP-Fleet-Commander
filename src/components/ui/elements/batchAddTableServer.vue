<template>
    <div>
        <b-button
            v-if="!noRefreshButton"
            size="sm" variant="primary" :disabled="refreshInProgress"
            class="mb-1"
            @click="refreshServers"
            v-b-tooltip.hover="'Test all servers'">
            <i :class="['fas fa-sync-alt', refreshInProgress ? 'fa-spin' : '']"></i>
            Fetch server status
        </b-button>
        <b-table
            small
            ref="selectableTable"
            :items="localServers"
            :fields="table.fields"
            @row-selected="onRowSelected"
            selected-variant="table-none"
            tbody-tr-class="no-outline"
            selectable
        >
            <template v-slot:head(selected)>
                <b-form-checkbox
                    id="checkbox-select-head"
                    @change="setCheckOnServers"
                ></b-form-checkbox>
            </template>

            <template v-slot:cell(selected)="row">
                <b-form-checkbox
                    :id="`checkbox-select-${row.index}`"
                    v-model="row.rowSelected"
                ></b-form-checkbox>
            </template>
            <template v-slot:cell(status)="row">
                <div 
                    class="d-flex align-items-center"
                >
                    <b-badge 
                        v-if="row.item.testResult.message !== undefined && row.item.testResult.message !== undefined"
                        :variant="row.item.testResult.color"
                    >
                        <div>{{ row.item.testResult.message }}</div>
                        <div>{{ row.item.testResult.version }}</div>
                    </b-badge>
                    <userPerms
                        v-if="row.item.userResult !== undefined && row.item.userResult.Role !== undefined"
                        :perms="row.item.userResult.Role"
                        :row_id="row.index"
                        context="batchadd"
                        class="ml-1"
                    ></userPerms>
                </div>
            </template>
            <template v-slot:cell(name)="row">
                <b-form-input
                    v-model="row.item.Server.name"
                ></b-form-input>
            </template>
            <template v-slot:cell(skip_ssl)="row">
                <b-form-checkbox v-model="row.item.skip_ssl" switch>
                </b-form-checkbox>
            </template>
            <template v-slot:cell(authkey)="row">
                <b-form-input
                    v-model="row.item.Server.authkey"
                ></b-form-input>
            </template>
        </b-table>
    </div>
</template>

<script>
import axios from "axios"
import userPerms from "@/components/ui/elements/userPerms.vue"

export default {
    name: "batchAddTableServer",
    components: {
        userPerms
    },
    props: {
        servers: {
            type: Array,
            required: true
        },
        skip_ssl: {
            type: Boolean,
            required: true
        },
        noRefreshButton: {
            type: Boolean,
            default: false
        },
        selectedServers: {
            type: Array,
            default: function() { return [] }
        }
    },
    data: function() {
        return {
            table: {
                allChecked: false,
                fields: [
                    {key: "selected", label: ""},
                    "status",
                    "name",
                    "Server.url",
                    "authkey",
                    "skip_ssl"
                ]
            },
            localServers: this.makeLocalServers(),
            selectedItems: [],
            recursiveChecked: false,
            refreshInProgress: false,
        }
    },
    computed: {
    },
    methods: {
        makeLocalServers() {
            let localServers = []
            localServers = this.servers.slice()
            localServers.forEach(server => {
                server.selected = false
            })
            return localServers
        },
        onRowSelected(items) {
            this.selectedItems = items
            this.$emit("update:selectedItems", this.selectedItems)
        },
        setSkipSslForAllServers() {
            this.localServers.forEach(server => {
                server.skip_ssl = this.skip_ssl
            })
        },
        setCheckOnServers(checked) {
            if (checked) {
                this.$refs.selectableTable.selectAllRows()
            } else {
                this.$refs.selectableTable.clearSelected()
            }
        },
        refreshServers() {
            this.refreshInProgress = true
            const url = "http://127.0.0.1:5000/servers/batchTest"
            let payload = this.createValidServerForm(this.localServers)
            axios.post(url, payload)
                .then((response) => {
                    this.localServers.forEach((loServer, index) => {
                        let reServer = response.data.find(reServer => {
                            return loServer.Server.name == reServer.name && loServer.Server.url == reServer.url && loServer.Server.authkey == reServer.authkey
                        })
                        loServer.testResult = reServer.testResult
                        loServer.userResult = reServer.userResult
                        if (reServer.testResult.color == "success") {
                            this.$refs.selectableTable.selectRow(index)
                        }
                    })
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not test Servers",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.refreshInProgress = false
                })
        },
        createValidServerForm(servers) {
            let serverList = []
            servers.forEach(server => {
                serverList.push({
                    name: server.Server.name,
                    skip_ssl: server.skip_ssl,
                    url: server.Server.url,
                    authkey: server.Server.authkey
                })
            })
            return serverList
        }
    },
    watch: {
        skip_ssl: function(newValue) {
            this.localServers.forEach(server => {
                server.skip_ssl = newValue
            })
        },
        authkey: function(newValue) {
            this.localServers.forEach(server => {
                server.authkey = newValue
            })
        },
        servers: function() {
            this.localServers = this.makeLocalServers()
        }
    }
}
</script>

<style scoped>
table >>> .no-outline {
    outline: none;
}
</style>