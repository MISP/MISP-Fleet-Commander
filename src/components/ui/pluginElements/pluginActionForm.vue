<template>
    <b-form @submit.prevent="submitAction">
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
                v-model="formData[param.key]"
                :options="param.options"
            >
                <template #first>
                    <b-form-select-option :value="null" disabled>-- Please select an option --</b-form-select-option>
                </template>
            </b-form-select>

            <b-form-checkbox-group
                v-else-if="param.type == 'checkbox'"
                :id="`input-${i}`"
                v-model="formData[param.key]"
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
                v-model="formData[param.key]"
                :type="param.type"
                placeholder="param.placeholder"
            ></b-form-input>

        </b-form-group>

        <b-button type="submit" variant="primary">Submit</b-button>
    </b-form>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import Vue from "vue"

export default {
    name: "pluginActionForm",
    components: {
    },
    props: {
        plugin: {
            type: Object,
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
        submitAction: function() {
            const finalData = {
                plugin_id: this.plugin.id,
                form_data: { ...this.formData }
            }
            this.$emit("pluginActionFormSubmit", finalData)
        }
    },
    created() {
        this.plugin.action_parameters.forEach(param => {
            Vue.set(this.formData, param.key, null)
        })
    }
}
</script>

<style scoped>

</style>