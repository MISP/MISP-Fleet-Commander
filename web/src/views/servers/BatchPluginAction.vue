<template>
    <b-modal
        :id="modalId"
        title="Batch Plugin Action"
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

        <b-card no-body>
            <b-tabs pills card vertical>
                <b-tab
                    v-for="plugin in actionPlugins"
                    v-bind:key="plugin.id"
                    :title="plugin.name"
                    lazy
                >
                    <template #title>
                        <i v-if="plugin.icon" :class="[plugin.icon, 'fa-fw mr-1']" style="width: 1rem;"></i>
                        {{ plugin.name }}
                    </template>
                    <div>
                        <h6 class="mb-0">
                            <i v-if="plugin.icon" :class="[plugin.icon, 'fa-fw mr-1']" style="width: 1rem;"></i>
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

<script>
import { mapState, mapGetters } from "vuex"
import JobRunPanel from "@/components/jobs/JobRunPanel.vue"
import pluginActionForm from "@/components/ui/pluginElements/pluginActionForm.vue"
import jobRunner from "@/helpers/jobRunnerMixin"

// The action runs as a job: the modal can be closed while it runs, its results stay here and on the job page
export default {
    name: "BatchPluginAction",
    components: {
        JobRunPanel,
        pluginActionForm,
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
            modalId: "modal-batch-plugin-action-selected",
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
            return this.server_ids.map(server_id => this.servers[server_id]).filter(server => server)
        },
    },
    methods: {
        handlePluginActionSubmit: function ({plugin_id, form_data}) {
            return this.startJob({
                kind: "plugin_action",
                server_ids: this.server_ids,
                params: { plugin_id, data: form_data },
            })
        },
    },
}
</script>
