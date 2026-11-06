<template>
    <b-modal 
        id="modal-discover-servers-result"
        title="Discover connected servers"
        size="xl"
        scrollable
        @hidden="resetModal"
        @ok.prevent="handleSubmission"
    >
        <small class="text-muted d-block">Find the MISP servers this one is connected to, using its remote servers index.</small>
        <small class="text-muted d-block">MISP does not share the authkeys of its remote servers: enter a key for each server you want to add, then test them before saving.</small>
        <h5>Root server</h5>
        <b-form inline>
            <div class="d-flex w-100 mb-2">
                <b-input-group class="w-50">
                    <b-input
                        placeholder="URL"
                        :value="rootServer.url"
                        disabled
                    ></b-input>
                    <template v-slot:append>
                        <b-input-group-text>
                            <b-form-checkbox :checked="rootServer.skip_ssl" class="force-custom-va" disabled switch>
                                <small>Skip SSL</small>
                            </b-form-checkbox>
                        </b-input-group-text>
                    </template>
                </b-input-group>
                <b-input
                    class="w-50 ml-2"
                    placeholder="AuthKey"
                    :value="rootServer.authkey_hint"
                    disabled
                ></b-input>
            </div>
        </b-form>

        <div class="mb-1">
            <b-button
                size="sm" variant="primary" :disabled="refreshInProgress"
                @click="discoverServer"
            >
                <i :class="['fas fa-search', refreshInProgress ? 'fa-spin' : '']"></i>
                Discover connected servers
            </b-button>
            <b-button
                v-if="discoveredServers.length > 0"
                size="sm" variant="outline-primary" class="ml-1"
                :disabled="testInProgress || !anyServerHasAuthkey"
                v-b-tooltip.hover="'Test the servers for which an authkey has been entered'"
                @click="testServers"
            >
                <i :class="['fas fa-plug', testInProgress ? 'fa-spin' : '']"></i>
                Test authkeys
            </b-button>
        </div>

        <batchAddTableServer
            ref="serverTable"
            :servers="discoveredServers"
            :busy="table.busy"
            :skip_ssl="false"
            :noRefreshButton="true"
            :selectedItems.sync="selectedServers"
            @update:refreshInProgress="testInProgress = $event"
        ></batchAddTableServer>

        <template v-slot:modal-footer="{ ok, cancel }">
            <small v-if="haveSelectedServers && !allSelectedHaveAuthkey" class="text-muted mr-auto">
                Enter a 40-character authkey for each selected server
            </small>
            <b-button variant="primary" @click="ok()" :disabled="!haveSelectedServers || !allSelectedHaveAuthkey || postInProgress">
                <b-spinner 
                    small
                    v-if="postInProgress"
                ></b-spinner>
                <span class="sr-only">Saving...</span>
                <span v-if="!postInProgress">Save</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/servers"
import batchAddTableServer from "@/views/servers/elements/batchAddTableServer.vue"

export default {
    name: "DiscoverServers",
    components: {
        batchAddTableServer
    },
    props: {
        rootServer: {
            type: Object,
            required: true
        },
        items: {
            type: Array,
        }
    },
    data: function() {
        return {
            table: {
                busy: false,
                fields: [
                    "selected",
                    "status",
                    "name",
                    "url",
                    "authkey",
                    "skip_ssl"
                ]
            },
            refreshInProgress: false,
            testInProgress: false,
            postInProgress: false,
            discoveredServers: [],
            selectedServers: [],
        }
    },
    computed: {
        haveSelectedServers() {
            return this.selectedServers.length > 0
        },
        anyServerHasAuthkey() {
            return this.discoveredServers.some(server => server.Server.authkey)
        },
        allSelectedHaveAuthkey() {
            return this.selectedServers.every(server => /^[a-zA-Z0-9]{40}$/.test(server.Server.authkey || ""))
        },
    },
    methods: {
        resetModal() {
            this.refreshInProgress = false
            this.postInProgress = false
            this.selectedServers = []
            this.discoveredServers = []
        },
        handleSubmission() {
            this.postInProgress = true
            let payload = this.createValidServerForm(this.selectedServers)
            this.$store.dispatch("servers/add", payload)
                .then(() => {
                    this.$emit("addition-success")
                    this.$bvModal.hide("modal-discover-servers-result")
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not add server",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.postInProgress = false
                })
        },
        testServers() {
            this.$refs.serverTable.refreshServers()
        },
        discoverServer() {
            this.table.busy = true
            this.refreshInProgress = true
            api.discoverConnected(this.rootServer.id)
                .then((discoveredServers) => {
                    discoveredServers.forEach(server => {
                        this.$set(server.Server, "authkey", "")
                    })
                    this.discoveredServers = discoveredServers
                })
                .catch(error => {
                    this.$bvToast.toast(error.response?.statusText || String(error), {
                        title: "Could not reach root server",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.refreshInProgress = false
                    this.table.busy = false
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
    }
}
</script>

<style scoped>
.force-custom-va >>> label {
    display: inline-block !important;
}
</style>
