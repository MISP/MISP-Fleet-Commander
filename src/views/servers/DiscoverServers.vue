<template>
    <b-modal 
        id="modal-discover-servers-result"
        title="Servers discovered recursively"
        size="xl"
        scrollable
        @hidden="resetModal"
        @ok.prevent="handleSubmission"
    >
        <small class="text-muted d-block">Try to add other MISP Servers connected to this one using the known remote servers index.</small>
        <small class="text-muted d-block">Behind the scenes, it fetches the index and the authey of associated users and save them locally.</small>
        <h5>Root server</h5>
        <b-form inline>
            <div class="d-flex w-100 mb-2">
                <b-input-group class="w-50">
                    <b-input
                        placeholder="URL"
                        v-model="rootServer.url"
                        disabled
                    ></b-input>
                    <template v-slot:append>
                        <b-input-group-text>
                            <b-form-checkbox v-model="rootServer.skip_ssl" class="force-custom-va" disabled switch>
                                <small>Skip SSL</small>
                            </b-form-checkbox>
                        </b-input-group-text>
                    </template>
                </b-input-group>
                <b-input
                    class="w-50 ml-2"
                    placeholder="AuthKey"
                    v-model="rootServer.authkey"
                    disabled
                ></b-input>
            </div>
        </b-form>

        <b-button
            size="sm" variant="primary" :disabled="refreshInProgress"
            class="mb-1"
            @click="discoverServer"
        >
            <i :class="['fas fa-sync-alt', refreshInProgress ? 'fa-spin' : '']"></i>
            Discover connected server
        </b-button>

        <batchAddTableServer
            :servers="discoveredServers"
            :busy="table.busy"
            :skip_ssl="false"
            :noRefreshButton="true"
            :selectedItems.sync="selectedServers"
        ></batchAddTableServer>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="primary" @click="ok()" :disabled="!haveSelectedServers || postInProgress">
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
import axios from "axios"
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
            postInProgress: false,
            discoveredServers: [],
            selectedServers: [],
        }
    },
    computed: {
        haveSelectedServers() {
            return this.selectedServers.length > 0
        }
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
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch latest version from GitHub",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.postInProgress = true
                })
        },
        discoverServer() {
            const url = "http://127.0.0.1:5000/servers/discoverConnected"
            this.table.busy = true
            this.refreshInProgress = true
            let server = {
                url: this.rootServer.url,
                authkey: this.rootServer.authkey,
                skip_ssl: this.rootServer.skip_ssl
            }
            axios.post(url, server)
                .then((response) => {
                    this.discoveredServers = response.data
                })
                .catch(error => {
                    this.$bvToast.toast(error.response.statusText, {
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