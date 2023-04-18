<template>
    <b-modal
        id="modal-batch-plugin-action-selected"
        title="Batch Plugin Action"
        size="xl"
        ok-only
    >

        <b-card
            :header="`${serverAmount} selected servers`"
            class="text-center mb-3"
            body-class="p-0 server-list-container"
        >
            <b-table-lite
                small striped borderless
                :fields="serverTableFields"
                :items="getServers"
            >
                <template #cell(response)="row">
                    <loaderPlaceholder class="d-flex justify-content-center" :loading="!requestInProgress[row.item.id]" maxWidth="100%" placeholderWidth="50%">
                        <div
                            v-if="serverResponse[row.item.id] !== undefined && serverResponse[row.item.id].status_code"
                            class="mb-0 d-flex"
                        >
                            <RequestResponseResult
                                :serverResponse="serverResponse[row.item.id]"
                            ></RequestResponseResult>
                            <b-button v-b-modal="`modal-response-${row.index}`" variant="primary" size="xs" class="ml-1">View</b-button>
                            <b-modal
                                :id="`modal-response-${row.index}`"
                                scrollable size="lg"
                                ok-only
                            >
                                <template #modal-header="">
                                    <RequestResponseResult
                                        :serverResponse="serverResponse[row.item.id]"
                                    ></RequestResponseResult>
                                    <b-button variant="link" size="sm" class="ml-auto p-0 m-0"
                                        @click="toggleRulesTreeMode"
                                    >
                                        <i :class="['fas', rulesTreeMode ? 'fa-code' : 'fa-stream']"></i>
                                    </b-button>
                                </template>

                                <jsonViewer 
                                    :tree="rulesTreeMode"
                                    :item="serverResponse[row.item.id].data"
                                    rootKeyName="Reponse data"
                                    :open="true"
                                ></jsonViewer>
                            </b-modal>
                        </div>
                    </loaderPlaceholder>
                </template>

            </b-table-lite>
        </b-card>

        <b-card no-body>
            <b-tabs pills card vertical>
                <b-tab
                    v-for="plugin in actionPlugins"
                    v-bind:key="plugin.id"
                    :title="plugin.name"
                    lazy
                >
                    <div>
                        <h6 class="mb-0">
                            <i v-if="plugin.icon" :class="[plugin.icon, 'mr-1']" style="width: 1rem;"></i>
                            {{ plugin.name }}
                        </h6>
                        <div class="text-muted mb-3 ml-4" style="font-size: 0.875">{{ plugin.description }}</div>
                        <pluginActionForm
                            :plugin="plugin"
                            :submit_function="handlePluginActionSubmit"
                        ></pluginActionForm>
                    </div>
                </b-tab>
            </b-tabs>
        </b-card>
    </b-modal>

    
</template>

<style scoped>

</style>

<script>
import Vue from "vue"
import moment from "moment"
import { mapState, mapGetters } from "vuex"
import pluginAPI from "@/api/plugins"
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"
import RequestResponseResult from "@/components/ui/elements/RequestResponseResult.vue"
import pluginActionForm from "@/components/ui/pluginElements/pluginActionForm.vue"

export default {
    name: "BatchPluginAction",
     components: {
        loaderPlaceholder,
        jsonViewer,
        RequestResponseResult,
        pluginActionForm,
    },
    props: {
        server_ids: {
            type: Array,
            required: true
        },
    },
    data: function() {
        return {
            serverTableFields: ['id', 'name', 'url', {key: 'response', class: ['align-middle']}],
            requestInProgress: {},
            serverResponse: {},
            rulesTreeMode: true,
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
        }),
        ...mapGetters({
            actionPlugins: "plugins/actionPlugins",
        }),
        getServers: function() {
            let serverList = []
            const allServer = this.servers
            this.server_ids.forEach((server_id) => {
                serverList.push(allServer[server_id])
            })
            return serverList
        },
        getServersForTable() {
            return this.getServers
        },
        serverAmount() {
            return this.getServers.length
        },
    },
    methods: {
        toggleRulesTreeMode() {
            this.rulesTreeMode = !this.rulesTreeMode
        },
         handlePluginActionSubmit: function ({plugin_id, form_data}) {
               return this.batchPluginAction(plugin_id, form_data)
        },
        batchPluginAction: function(plugin_id, form_data) {
            const that = this
            let actionPromises = []
            this.server_ids.forEach((server_id) => {
                that.requestInProgress[server_id] = true
                const actionPromise = pluginAPI.submitAction(server_id, plugin_id, form_data)
                    .then((response) => {
                        this.handlePluginResponse(server_id, response)
                        return response
                    })
                    .catch(error => {
                    })
                    .finally(() => {
                        that.requestInProgress[server_id] = false
                    })
                actionPromises.push(actionPromise)
            })
            return Promise.all(actionPromises)
                .then((responses) => {
                    const successes = responses.filter(response => {
                        return response.statusText == 'OK'
                    });
                    if (successes.length > 0) {
                        const successMessage = successes[0].data.data.message
                        this.$bvToast.toast(successMessage, {
                            title: `Successfully performed ${successes.length} action(s)`,
                            variant: "success",
                        })
                    } else {
                        const errorMessage = responses[0].data.data.message
                        this.$bvToast.toast(errorMessage, {
                            title: "Could not perform any action",
                            variant: "danger",
                        })
                    }
                })
                .catch(error => {
                    const errorMessage = error.toJSON().message
                    this.$bvToast.toast(errorMessage, {
                        title: "Could not perform action",
                        variant: "danger",
                    })
                })
        },
        handlePluginResponse(server_id, response) {
            Vue.set(this.serverResponse, server_id, {
                status_code: response.status,
                // reason: response.data.data.message,
                url: response.data.data.url,
                data: response.data.data,
                elapsed_time: '',
                // elapsed_time: moment.duration(response.data.data._latency, 'seconds'),
            })
        },
        resetRequestInProgress() {
            Object.keys(this.requestInProgress).forEach(server_id => {
                Vue.delete(this.requestInProgress, server_id)
            })
        },
        updateRequestInProgress(newIDs) {
            this.resetRequestInProgress()
            newIDs.forEach((server_id) => {
                Vue.set(this.requestInProgress, server_id, false)
                Vue.set(this.serverResponse, server_id, {})
            })
        }
    },
    watch: {
        server_ids(newIDs, oldIDs) {
            this.updateRequestInProgress(newIDs)
        }
    },
    beforeMount() {
        this.updateRequestInProgress(this.server_ids)
    }
}
</script>

<style scoped>
.server-list-container {
    max-height: 300px;
    overflow: auto;
}
</style>
