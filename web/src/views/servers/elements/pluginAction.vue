<template>
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
</template>

<script>
import { mapState, mapGetters } from "vuex"
import Vue from "vue"
import pluginActionForm from "@/components/ui/pluginElements/pluginActionForm.vue"
import pluginAPI from "@/api/plugins"

export default {
    name: "pluginAction",
    components: {
        pluginActionForm
    },
    props: {
        server_id: {
            type: Number,
            required: true
        },
    },
    data: function() {
        return {
        }
    },
    computed: {
        ...mapGetters({
            actionPlugins: "plugins/actionPlugins",
        }),
    },
    methods: {
        handlePluginActionSubmit: function ({plugin_id, form_data}) {
            return pluginAPI.submitAction(this.server_id, plugin_id, form_data)
                .then((response) => {
                    if (response.data.error) {
                        const errorMessage = response.data.error.join(', ')
                        this.$bvToast.toast(errorMessage, {
                            title: `Could not perform action for plugin ${plugin_id}`,
                            variant: "danger",
                        })
                    } else {
                        const successMessage = response.data.data.message
                        this.$bvToast.toast(successMessage, {
                            title: `Successfully performed action for plugin ${plugin_id}`,
                            variant: "success",
                        })
                    }
                })
                .catch(error => {
                    const errorMessage = error.toJSON().message
                    this.$bvToast.toast(errorMessage, {
                        title: `Could not perform action for plugin ${plugin_id}`,
                        variant: "danger",
                    })
                })
        },
    },
}
</script>

<style scoped>

</style>