<template>
    <b-modal
        id="modal-batch-api-selected"
        title="Batch API call"
        size="xl"
        ok-only
    >

        <b-card
            header="Selected servers"
            class="text-center mb-3"
            body-class="p-0"
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

        <b-form @submit="onSubmit">
            <b-form-row>
                <b-col cols="2">
                    <b-form-group
                        label="HTTP Method:"
                        label-for="input-method"
                    >
                        <b-form-select v-model="form.method" :options="options"></b-form-select>
                    </b-form-group>
                </b-col>
                <b-col>
                    <b-form-group
                        label="URL:"
                        label-for="input-url"
                        description="Relative URL (e.g. `/events/index`)"
                    >
                        <b-form-input
                            id="input-url"
                            v-model="form.url"
                            type="text"
                            placeholder="Enter URL"
                            required
                        ></b-form-input>
                    </b-form-group>
                </b-col>
                <b-col cols="1" class="d-flex align-items-center">
                    <b-button type="submit" variant="primary" class="mb-2">Submit</b-button>
                </b-col>
            </b-form-row>

            <b-form-group label="Body:" label-for="input-body">
            <b-form-textarea
                id="input-body"
                v-model="form.body"
                placeholder="Enter POST data"
                rows="4"
                ></b-form-textarea>
            </b-form-group>
        </b-form>
    </b-modal>

    
</template>

<style scoped>

</style>

<script>
import store from "@/store/index"
import api from "@/api/servers"
import { mapState, mapGetters } from "vuex"
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"
import RequestResponseResult from "@/components/ui/elements/RequestResponseResult.vue"

export default {
    name: "BatchAPI",
     components: {
        loaderPlaceholder,
        jsonViewer,
        RequestResponseResult,
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
            form: {
                url: "/servers/getVersion",
                method: "POST",
                body: "",
                parsedBody: {}
            },
            options: [
                { value: "POST", text: "POST" },
                { value: "GET", text: "GET" },
            ],
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
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
            let serversForTable = []
            const that = this
            this.getServers.forEach(server => {
                let serverCopy = Object.assign({}, server)
                serverCopy.response = that.serverResponse[server.id] ?? {}
                serverCopy.request_in_progress = that.requestInProgress[server.id] ?? false
                serversForTable.push(serverCopy)
            });
            return serversForTable
        },
    },
    methods: {
        batchAPICall(payload) {
            let that = this
            this.server_ids.forEach((server_id) => {
                that.requestInProgress[server_id] = true
            })
            api.batchRestQuery(this.server_ids, payload)
                .then((responses) => {
                    this.handleQueryResponse(responses)
                })
        },
        onSubmit(event) {
            event.preventDefault()
            if (this.form.body.length == 0) {
                this.form.body = "{}"
            }
            const jsonValidation = this.checkBody()
            if (jsonValidation !== true) {
                this.$bvToast.toast(jsonValidation, {
                    title: "Body is not a valid JSON",
                    variant: "danger",
                    solid: true
                })
                return
            }
            const payload = {
                url: this.form.url,
                data: this.form.body,
                method: this.form.method
            }
            this.batchAPICall(payload)
        },
        checkBody() {
            try {
                this.form.parsedBody = JSON.parse(this.form.body)
            } catch (error) {
                return error.message
            }
            return true
        },
        handleQueryResponse(responses) {
            const that = this
            responses.forEach((response) => {
                const server_id = response.data.server_id
                that.requestInProgress[server_id] = false
                this.$set(that.serverResponse, server_id, {
                    status_code: response.data.status_code,
                    reason: response.data.reason,
                    url: response.data.url,
                    data: response.data.data,
                    headers: response.data.headers,
                    elapsed_time: response.data.elapsed_time,
                })
            })
        },
        toggleRulesTreeMode() {
            this.rulesTreeMode = !this.rulesTreeMode
        },
    },
    beforeUpdate: function () {
        this.server_ids.forEach((server_id) => {
            this.$set(this.requestInProgress, server_id, false)
            this.$set(this.serverResponse, server_id, {})
        })
    },
}
</script>

<style scoped>
</style>