<template>
    <div>
        <b-card class="" no-body>
            <template #header>
                <div class="d-flex">
                    <loaderPlaceholder class="d-flex flex-grow-1" :loading="!requestInProgress" maxWidth="50%"
                        placeholderWidth="100%">
                        <div class="mb-0 d-flex flex-fill">
                            <span class="font-weight-bold mr-3">
                                <b-icon :class="statusCodeColorClass" icon="circle-fill"></b-icon>
                                {{ validResponse.status_code }}
                                {{ validResponse.reason }}
                            </span>
                            <span class="text-mono font-weight-light">{{ validResponse.url }}</span>
                            <span class="ml-auto text-muted">
                                <span class="mr-3">{{ elapsed_time_printable }}</span>
                                <span>{{ contentLengthPrintable }}</span>
                            </span>
                        </div>
                    </loaderPlaceholder>
                    <loaderPlaceholder class="d-flex flex-grow-1 justify-content-end" v-if="requestInProgress"
                        :loading="!requestInProgress" maxWidth="100%" placeholderWidth="25%"></loaderPlaceholder>
                </div>
            </template>
            <b-tabs pills card end content-class="max-height-300">
                <b-tab title="Response Text" active>
                    <loaderPlaceholder :loading="!requestInProgress" maxWidth="">
                        <pre class="m-0" style="white-space: break-spaces;">{{ validResponse.data }}</pre>
                    </loaderPlaceholder>
                </b-tab>
                <b-tab title="Response JSON">
                    <loaderPlaceholder :loading="!requestInProgress" maxWidth="">
                        <jsonViewer :item="responseDataJson" :open="true"></jsonViewer>
                    </loaderPlaceholder>
                </b-tab>
                <b-tab title="Response Headers">
                    <loaderPlaceholder :loading="!requestInProgress" maxWidth="">
                        <b-table-simple striped small class="mb-0" :bordered="false" :borderless="true" :outlined="false">
                            <b-tbody>
                                <b-tr v-for="(v, k) in validResponse.headers" v-bind:key="k">
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
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"

export default {
    name: "APIResponsePanel",
    components: {
        jsonViewer,
        loaderPlaceholder
    },
    props: {
        response: {
            required: true,
            type: Object,
        },
        requestInProgress: {
            required: true,
            type: Boolean,
        },
    },
    data: function () {
        return {
            emptyResponse: {
                elapsed_time: "",
                status_code: "",
                data: "",
                headers: {},
            },
        }
    },
    computed: {
        validResponse() {
            return this.response.status_code ? this.response : this.emptyResponse
        },
        statusCodeColorClass() {
            if (String(this.validResponse.status_code) === "") {
                return "text-secondary"
            }
            if (String(this.validResponse.status_code).startsWith("2")) {
                return "text-success"
            } else if (String(this.validResponse.status_code).startsWith("5")) {
                return "text-danger"
            } else {
                return "text-warning"
            }
        },
        responseDataJson() {
            return typeof this.validResponse.data === "object" ? this.validResponse.data : { "Error": "Response is not a valid JSON" }
        },
        elapsed_time_printable() {
            let text = ""
            if (this.validResponse.elapsed_time !== "") {
                let [h, m, s] = this.validResponse.elapsed_time.split(":")
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
                text += String(parseInt(ms) / 1000) + "ms"
            }
            return text
        },
        contentLengthPrintable() {
            let text = ""
            const contentLength = this.validResponse.headers["Content-Length"]
            if (contentLength !== undefined) {
                text = contentLength + " B"
                if (contentLength / (1024 * 1024) < 1) {
                    text = (contentLength / 1024).toFixed(2) + " kB"
                } else if (contentLength / (1024 * 1024 * 1024) < 1) {
                    text = (contentLength / (1024 * 1024)).toFixed(2) + " MB"
                }
            } else {
                text = "0 B"
            }
            return text
        }
    },
    methods: {
    },
}
</script>
