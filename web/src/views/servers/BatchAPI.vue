<template>
    <b-modal
        :id="modalId"
        title="Batch API call"
        size="xl"
        ok-only
        ok-title="Close"
        ok-variant="secondary"
    >
        <JobRunPanel
            :job="job"
            :servers="getServers"
            @navigate="$bvModal.hide(modalId)"
            @retried="followJob"
        ></JobRunPanel>

        <b-form @submit="onSubmit">
            <b-form-row>
                <b-col cols="12" sm="3" md="2">
                    <b-form-group
                        label="HTTP Method:"
                        label-for="batch-api-method"
                    >
                        <b-form-select id="batch-api-method" v-model="form.method" :options="options"></b-form-select>
                    </b-form-group>
                </b-col>
                <b-col>
                    <b-form-group
                        label="URL:"
                        label-for="batch-api-url"
                        description="A path on the MISP servers (e.g. `/events/index`)"
                        :state="urlState"
                        invalid-feedback="Only paths on the MISP servers can be queried, not other hosts"
                    >
                        <b-form-input
                            id="batch-api-url"
                            v-model="form.url"
                            type="text"
                            placeholder="/servers/getVersion"
                            :state="urlState"
                            required
                        ></b-form-input>
                    </b-form-group>
                </b-col>
                <b-col cols="12" sm="auto" class="d-flex align-items-center">
                    <b-button type="submit" variant="primary" class="mb-2" :disabled="submitting || urlState === false">
                        <b-spinner v-if="submitting" small class="mr-1"></b-spinner>Submit
                    </b-button>
                </b-col>
            </b-form-row>
            <b-form-group
                v-if="form.method === 'POST'"
                label="Body:"
                label-for="batch-api-body"
                description="JSON sent to every server. Credentials in it are kept encrypted and shown as *** in the job."
            >
                <b-form-textarea
                    id="batch-api-body"
                    v-model="form.body"
                    placeholder="{}"
                    rows="4"
                    class="text-monospace"
                ></b-form-textarea>
            </b-form-group>
        </b-form>
    </b-modal>
</template>

<script>
import { mapState } from "vuex"
import JobRunPanel from "@/components/jobs/JobRunPanel.vue"
import jobRunner from "@/helpers/jobRunnerMixin"

// The query runs as a job: the modal can be closed while it runs, its results stay here and on the job page
export default {
    name: "BatchAPI",
    components: {
        JobRunPanel,
    },
    mixins: [jobRunner],
    props: {
        server_ids: {
            type: Array,
            required: true
        },
    },
    data: function() {
        return {
            modalId: "modal-batch-api-selected",
            submitting: false,
            form: {
                url: "/servers/getVersion",
                method: "GET",
                body: "",
            },
            options: [
                { value: "GET", text: "GET" },
                { value: "POST", text: "POST" },
            ],
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
        }),
        getServers: function() {
            return this.server_ids.map(server_id => this.servers[server_id]).filter(server => server)
        },
        // Same rule as the backend: a path, never another host
        urlState() {
            const url = this.form.url.trim()
            if (url === "") {
                return null
            }
            return /^[a-z][a-z0-9+.-]*:/i.test(url) || url.startsWith("//") ? false : null
        },
    },
    methods: {
        onSubmit(event) {
            event.preventDefault()
            let data = null
            if (this.form.method === "POST") {
                const body = this.form.body.trim() === "" ? "{}" : this.form.body
                try {
                    JSON.parse(body)
                } catch (error) {
                    this.$bvToast.toast(error.message, {
                        title: "Body is not a valid JSON",
                        variant: "danger",
                        solid: true
                    })
                    return
                }
                data = body
            }
            this.submitting = true
            this.startJob({
                kind: "rest_query",
                server_ids: this.server_ids,
                params: { method: this.form.method, url: this.form.url.trim(), data },
            }).finally(() => {
                this.submitting = false
            })
        },
    },
}
</script>
