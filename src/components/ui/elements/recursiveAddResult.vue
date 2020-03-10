<template>
    <b-modal 
        id="modal-recursive-add-result"
        title="Servers discovered recursively"
        size="xl"
        scrollable
        @hidden="resetModal"
        @ok="handleSubmission"
    >
        <h5>Root server</h5>
        <b-form inline>
            <div class="d-flex w-100 mb-2">
                <b-input-group class="w-50">
                    <b-input
                        placeholder="URL"
                        v-model="rootServer.url"
                    ></b-input>
                    <template v-slot:append>
                        <b-input-group-text>
                            <b-form-checkbox v-model="rootServer.skip_ssl" class="force-custom-va" switch>
                                <small>Skip SSL</small>
                            </b-form-checkbox>
                        </b-input-group-text>
                    </template>
                </b-input-group>
                <b-input
                    class="w-50 ml-2"
                    placeholder="AuthKey"
                    v-model="rootServer.authkey"
                ></b-input>
            </div>
        </b-form>

        <b-button
            size="sm" variant="primary" :disabled="refreshInProgress"
            class="mb-1"
            @click="discoverServer"
            v-b-tooltip.hover="'Discover connected servers'">
            <i :class="['fas fa-sync-alt', refreshInProgress ? 'fa-spin' : '']"></i>
            Discover connected server
        </b-button>

        <batchAddTableServer
            :servers="discoveredServers"
            :skip_ssl="false"
            :noRefreshButton="true"
        ></batchAddTableServer>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="primary" @click="ok()" :disabled="!haveElligibleServers">
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
import batchAddTableServer from "@/components/ui/elements/batchAddTableServer.vue"

export default {
    name: "recursiveAddRestul",
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
            // required: true
        }
    },
    data: function() {
        return {
            table: {
                allChecked: false,
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
            discoveredServers: [],
            postInProgress: false,
            haveElligibleServers: false
        }
    },
    methods: {
        resetModal() {
        },
        handleSubmission() {
        },
        discoverServer() {
            const url = "http://127.0.0.1:5000/servers/discoverConnected"
            this.postInProgress = true
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
                    this.postInProgress = false
                })
        }
    }
}
</script>

<style scoped>
.force-custom-va >>> label {
    display: inline-block !important;
}
</style>