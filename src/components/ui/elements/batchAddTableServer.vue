<template>
    <div>
        <b-button
            size="sm" variant="primary" :disabled="refreshInProgress"
            @click="refreshServers"
            v-b-tooltip.hover="'Test all servers'">
            <i :class="['fas fa-sync-alt', refreshInProgress ? 'fa-spin' : '']"></i>
            Fetch server status
        </b-button>
        <b-table-lite
            small
            :items="getLocalServers"
            :fields="table.fields"
        >
            <template v-slot:head(select)>
                <b-form-checkbox
                    id="checkbox-select-head"
                    v-model="table.allChecked"
                    @change="setCheckOnServers"
                ></b-form-checkbox>
            </template>

            <template v-slot:cell(select)="row">
                <b-form-checkbox
                    :id="`checkbox-select-${row.index}`"
                    v-model="row.item.select.selected"
                    :disabled="row.item.select.disabled"
                ></b-form-checkbox>
            </template>
            <template v-slot:cell(status)="row">
                <div class="d-flex align-items-center">
                    <b-badge 
                        v-if="row.value.connection !== undefined && row.value.connection.message !== undefined"
                        :variant="row.value.connection.color"
                    >
                        <div>{{ row.value.connection.message }}</div>
                        <div>{{ row.value.connection.version }}</div>
                    </b-badge>
                    <userPerms
                        v-if="row.value.user !== undefined && row.value.user.Role !== undefined"
                        :perms="row.value.user.Role"
                        :row_id="row.index"
                        context="batchadd"
                        class="ml-1"
                    ></userPerms>
                </div>
            </template>
            <template v-slot:cell(name)="row">
                <b-form-input
                    v-model="row.item.name"
                ></b-form-input>
            </template>
            <template v-slot:cell(skip_ssl)="row">
                <b-form-checkbox v-model="row.item.skip_ssl" switch>
                </b-form-checkbox>
            </template>
            <template v-slot:cell(authkey)="row">
                <b-form-input
                    v-model="row.item.authkey"
                ></b-form-input>
            </template>
        </b-table-lite>
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
        authkey: {
            type: String
        }
    },
    data: function() {
        return {
            table: {
                allChecked: false,
                fields: [
                    {key: "select", label: ""},
                    "status",
                    "name",
                    "url",
                    "authkey",
                    "skip_ssl"
                ]
            },
            localServers: this.makeLocalServers(),
            recursiveChecked: false,
            refreshInProgress: false,
        }
    },
    computed: {
        getLocalServers() {
            return this.localServers
        }
    },
    methods: {
        makeLocalServers() {
            let localServers = []
            localServers = this.servers.slice()
            localServers.forEach(server => {
                server.selected = false
                server.skip_ssl = this.skip_ssl
            })
            return localServers
        },
        setSkipSslForAllServers() {
            this.localServers.forEach(server => {
                server.skip_ssl = this.skip_ssl
            })
        },
        setCheckOnServers(checked) {
            this.localServers.forEach(server => {
                server.select.selected = checked
            })
        },
        refreshServers() {
            this.refreshInProgress = true
            const url = "http://127.0.0.1:5000/servers/batchTest"
            axios.post(url, this.localServers)
                .then((response) => {
                    response.data.forEach(reServer => {
                        let loServer = this.localServers.find(loServer => {
                            return loServer.name == reServer.name && loServer.url == reServer.url && loServer.authkey == reServer.authkey
                        })
                        loServer.status.connection = reServer.testResult
                        loServer.status.user = reServer.userResult
                        if (reServer.testResult.color == "success") {
                            loServer.select.selected = true
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
</style>