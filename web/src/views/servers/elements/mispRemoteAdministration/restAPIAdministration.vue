<template>
    <div>
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

        <b-card
            class=""
            no-body
        >
            <template #header>
                <div class="d-flex">
                    <loaderPlaceholder class="d-flex flex-grow-1" :loading="!requestInProgress" maxWidth="50%" placeholderWidth="100%">
                    <div class="mb-0 d-flex flex-fill">
                        <span class="font-weight-bold mr-3">
                            <b-icon :class="statusCodeColorClass" icon="circle-fill"></b-icon>
                            {{ response.status_code }}
                            {{ response.reason }}
                        </span>
                        <span class="text-mono font-weight-light">{{ response.url }}</span>
                        <span class="ml-auto text-muted">
                            <span class="mr-3">{{ elapsed_time_printable }}</span>
                            <span>{{ contentLengthPrintable }}</span>
                        </span>
                    </div>
                    </loaderPlaceholder>
                    <loaderPlaceholder class="d-flex flex-grow-1 justify-content-end" v-if="requestInProgress" :loading="!requestInProgress" maxWidth="100%" placeholderWidth="25%"></loaderPlaceholder>
                </div>
            </template>
            <b-tabs 
                pills card end
                content-class="max-height-300"
            >
                <b-tab title="Response Text" active>
                    <loaderPlaceholder :loading="!requestInProgress" maxWidth="">
                    <pre class="m-0" style="white-space: break-spaces;">{{ response.data }}</pre>
                    </loaderPlaceholder>
                </b-tab>
                <b-tab title="Response JSON">
                    <loaderPlaceholder :loading="!requestInProgress" maxWidth="">
                    <jsonViewer
                        :item="responseDataJson"
                        :open="true"
                    ></jsonViewer>
                    </loaderPlaceholder>
                </b-tab>
                <b-tab title="Response Headers">
                    <loaderPlaceholder :loading="!requestInProgress" maxWidth="">
                    <b-table-simple
                        striped small
                        class="mb-0"
                        :bordered="false"
                        :borderless="true"
                        :outlined="false"
                    >
                        <b-tbody>
                            <b-tr v-for="(v, k) in response.headers" v-bind:key="k">
                                <b-th class="text-nowrap">{{ k }}</b-th>
                                <b-td>{{ v }}</b-td>
                            </b-tr>
                        </b-tbody>
                    </b-table-simple>
                    </loaderPlaceholder>
                </b-tab>
            </b-tabs>
        </b-card>
    </div>
</template>

<script>
import api from "@/api/servers"
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"

export default {
    name: "RestAPIAdministrationModal",
    components: {
        jsonViewer,
        loaderPlaceholder
    },
    props: {
        server: {
            required: true,
            type: Object
        },
    },
    data: function() {
        return {
            value: "",
            form: {
                url: "",
                method: "POST",
                body: "",
                parsedBody: {}
            },
            requestInProgress: false,
            options: [
                { value: "POST", text: "POST" },
                { value: "GET", text: "GET" },
            ],
            response: {
                elapsed_time: "",
                status_code: "",
                data: "",
                headers: {}
            }
        }
    },
    computed: {
        statusCodeColorClass() {
            if (String(this.response.status_code) === "") {
                return "text-secondary"
            }
            if (String(this.response.status_code).startsWith("2")) {
                return "text-success"
            } else if (String(this.response.status_code).startsWith("5")) {
                return "text-danger"
            } else {
                return "text-warning"
            }
        },
        responseDataJson() {
            return typeof this.response.data === "object" ? this.response.data : {"Error": "Response is not a valid JSON"}
        },
        elapsed_time_printable() {
            let text = ""
            if (this.response.elapsed_time !== "") {
                let [h, m, s] = this.response.elapsed_time.split(":")
                if (h !== "0") {
                    text += h + "h "
                }
                if (m !== "00") {
                    text += h + "m "
                }
                let ms = s.split(".")
                s = ms[0]
                ms = ms[1]
                if (s !== "00") {
                    text += s + "s "
                }
                text += String(parseInt(ms)/1000) + "ms"
            }
            return text
        },
        contentLengthPrintable() {
            let text = ""
            const contentLength = this.response.headers["Content-Length"]
            if (contentLength !== undefined) {
                text = contentLength + " B"
                if (contentLength / (1024*1024) < 1) {
                    text = (contentLength / 1024).toFixed(2) + " kB"
                } else if (contentLength / (1024*1024*1024) < 1) {
                    text = (contentLength / (1024*1024)).toFixed(2) + " MB"
                }
            } else {
                text = "0 B"
            }
            return text
        }
    },
    methods: {
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
            this.requestInProgress = true
            api.restQuery(
                this.server,
                payload,
                (response) => {
                    this.handleQueryResponse(response)
                    this.requestInProgress = false
                },
                (error) => {
                }
            )
        },
        checkBody() {
            try {
                this.form.parsedBody = JSON.parse(this.form.body)
            } catch (error) {
                return error.message
            }
            return true
        },
        handleQueryResponse(response) {
            this.response.status_code = response.status_code
            this.response.reason = response.reason
            this.response.url = response.url
            this.response.data = response.data
            this.response.headers = response.headers
            this.response.elapsed_time = response.elapsed_time
        }
    },
    created: function() {
    },
    updated: function() {
    }
}
</script>

<style scoped>
.max-height-300 > div.card-body {
    max-height: 300px;
    overflow-y: auto;
    padding: 0.5rem;
}
</style>