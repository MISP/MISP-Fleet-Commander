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
                    <div>
                        <b-form @submit.prevent="submitAction(plugin.id)">
                            <b-form-group
                                v-for="(param, i) in plugin.action_parameters"
                                :key="`${plugin.id}-${param.key}`"
                                :id="`${plugin.id}-${param.key}`"
                                :label="plugin.name"
                                :label-for="`input-${i}`"
                                :description="param.description"
                                class="col-lg-6 col-md-8"
                            >

                                <b-form-select
                                    v-if="param.type == 'select'"
                                    :id="`input-${i}`"
                                    v-model="formData[plugin.id][param.key]"
                                    :options="param.options"
                                >
                                    <template #first>
                                        <b-form-select-option :value="null" disabled>-- Please select an option --</b-form-select-option>
                                    </template>
                                </b-form-select>

                                <b-form-checkbox-group
                                    v-else-if="param.type == 'checkbox'"
                                    :id="`input-${i}`"
                                    v-model="formData[plugin.id][param.key]"
                                >
                                    <b-form-checkbox
                                        v-for="option, j in param.options"
                                        :key="`${plugin.id}-${param.key}-${j}`"
                                        :value="option.value"
                                    >option.text</b-form-checkbox>
                                </b-form-checkbox-group>

                                <b-form-input
                                    v-else
                                    :id="`input-${i}`"
                                    v-model="formData[plugin.id][param.key]"
                                    :type="param.type"
                                    placeholder="param.placeholder"
                                ></b-form-input>

                            </b-form-group>

                            <b-button type="submit" variant="primary">Submit</b-button>
                        </b-form>
                    </div>
                </div>
            </b-tab>
        </b-tabs>
  </b-card>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import Vue from "vue"
import pluginAPI from "@/api/plugins"

export default {
    name: "pluginAction",
    components: {
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
        submitAction: function(pluginID) {
            pluginAPI.submitAction(this.server_id, pluginID, this.formData)
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
        }
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