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
                        @pluginActionFormSubmit="handlePluginActionSubmit"
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
            formData: {},
        }
    },
    computed: {
        ...mapGetters({
            actionPlugins: "plugins/actionPlugins",
        }),
    },
    methods: {
        handlePluginActionSubmit: function ({plugin_id, form_data}) {
            pluginAPI.submitAction(this.server_id, plugin_id, form_data)
                .then((response) => {
                    const successMessage = response.data.data.message
                    this.$bvToast.toast(successMessage, {
                        title: "Successfully performed action",
                        variant: "success",
                    })
                })
                .catch(error => {
                    const errorMessage = error.toJSON().message
                    this.$bvToast.toast(errorMessage, {
                        title: "Could not perform action",
                        variant: "danger",
                    })
                })
        },
    },
    created() {
        this.actionPlugins.forEach(plugin => {
            Vue.set(this.formData, plugin.id, {})
            plugin.action_parameters.forEach(param => {
                Vue.set(this.formData[plugin.id], param.key, null)
            })
        });
    }
}
</script>

<style scoped>

</style>