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
            :busy="busy"
            :items="localServers"
            :fields="table.fields"
            @row-selected="onRowSelected"
            selected-variant="none"
            tbody-tr-class="no-outline"
            selectable
        >
            <template v-slot:table-busy>
                <div class="text-center text-danger my-2">
                <b-spinner class="align-middle"></b-spinner>
                <strong> Discovering connected servers...</strong>
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
                    placeholder="Authkey"
                    autocomplete="off"
                    :state="row.item.Server.authkey ? /^[a-zA-Z0-9]{40}$/.test(row.item.Server.authkey) : null"
                ></b-form-input>
            </template>
        </b-table>
    </div>
</template>

<script>
import api from "@/api/servers"
import userPerms from "@/views/servers/elements/userPerms.vue"

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
        busy: {
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
        selectRow(checked, index) {
            if (checked) {
                this.$refs.selectableTable.selectRow(index)
            } else {
                this.$refs.selectableTable.unselectRow(index)
            }
        },
        refreshServers() {
            // Only servers with an authkey are worth testing; keep the others' current status
            const testedIndexes = []
            this.localServers.forEach((server, index) => {
                if (server.Server.authkey) {
                    testedIndexes.push(index)
                }
            })
            if (testedIndexes.length == 0) {
                return
            }
            this.refreshInProgress = true
            this.$emit("update:refreshInProgress", true)
            let payload = this.createValidServerForm(testedIndexes.map(index => this.localServers[index]))
            api.batchTest(payload)
                .then((results) => {
                    // Results carry the position of the tested server in the payload, never its authkey
                    results.forEach(result => {
                        const localIndex = testedIndexes[result.index]
                        const loServer = this.localServers[localIndex]
                        if (loServer === undefined) {
                            return
                        }
                        this.$set(loServer, "testResult", result.testResult)
                        this.$set(loServer, "userResult", result.userResult)
                        if (result.testResult.color == "success") {
                            this.$refs.selectableTable.selectRow(localIndex)
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
                    this.$emit("update:refreshInProgress", false)
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
        servers: function() {
            this.localServers = this.makeLocalServers()
        }
    }
}
</script>

<style scoped>
</style>