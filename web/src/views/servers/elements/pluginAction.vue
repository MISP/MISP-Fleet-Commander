<template>
    <div>
        <h6 class="mb-0">
            <i v-if="plugin.icon" :class="[plugin.icon, 'mr-1']" style="width: 1rem;"></i>
            {{ plugin.name }}
        </h6>
        <div class="text-muted mb-3 ml-4" style="font-size: 0.875">{{ plugin.description }}</div>
        <pluginActionForm
            :plugin="plugin"
            :submit_function="handlePluginActionSubmit"
            @update:postInProgress="postInProgress = $event"
        ></pluginActionForm>

        <APIResponsePanel
            v-show="hasRequestResponse"
            class="mt-2"
            :response="formatedResponse"
            :requestInProgress="postInProgress"
        ></APIResponsePanel>
    </div>
</template>

<script>
import { mapGetters } from "vuex"
import pluginActionForm from "@/components/ui/pluginElements/pluginActionForm.vue"
import APIResponsePanel from "@/views/servers/elements/mispRemoteAdministration/APIResponsePanel"
import pluginAPI from "@/api/plugins"

export default {
    name: "pluginAction",
    components: {
        pluginActionForm,
        APIResponsePanel,
    },
    props: {
        server_id: {
            type: Number,
            required: true
        },
        plugin: {
            type: Object,
            required: true
        },
    },
    data: function() {
        return {
            postInProgress: false,
            response: {},
        }
    },
    computed: {
        ...mapGetters({
            actionPlugins: "plugins/actionPlugins",
        }),
        hasRequestResponse() {
            return this.response.data?.request_response !== undefined
        },
        formatedResponse() {
            const formatedResponse =  Object.assign({}, this.response.data?.request_response)
            formatedResponse.data = this.response.data?.data
            return formatedResponse
        }
    },
    methods: {
        getToastVariant(state) {
            if (state == 'success') {
                return 'success'
            } else if (state == 'fail' || state == 'error') {
                return 'danger'
            }
            return 'primary'
        },
        handlePluginActionSubmit: function ({plugin_id, form_data}) {
            return pluginAPI.submitAction(this.server_id, plugin_id, form_data)
                .then((response) => {
                    this.response = response
                    if (response.data.error) {
                        const errorMessage = response.data.error.join(', ')
                        this.$bvToast.toast(errorMessage, {
                            title: `Failure for plugin action ${plugin_id}`,
                            variant: "danger",
                        })
                    } else {
                        const successMessage = response.data.data.message
                        this.$bvToast.toast(successMessage, {
                            title: `Success for plugin action ${plugin_id}`,
                            variant: this.getToastVariant(response.data.status),
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