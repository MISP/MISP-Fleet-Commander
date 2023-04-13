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

            <b-form-textarea
                v-else-if="param.type == 'textarea'"
                :id="`input-${i}`"
                v-model="formData[param.key]"
                :type="param.type"
                :placeholder="param.placeholder || ''"
                rows="3"
                max-rows="6"
            ></b-form-textarea>

            <b-form-input
                v-else
                :id="`input-${i}`"
                v-model="formData[param.key]"
                :type="param.type"
                :placeholder="param.placeholder || ''"
            ></b-form-input>

        </b-form-group>

        <b-button variant="primary" type="submit" :disabled="postInProgress">
            <b-spinner 
                small
                v-if="postInProgress"
            ></b-spinner>
            <span class="sr-only">Submitting...</span>
            <span v-if="!postInProgress">Submit</span>
        </b-button>
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
        submit_function: {
            type: Function,
        }
    },
    data: function() {
        return {
            formData: {},
            postInProgress: false
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
            this.postInProgress = true
            this.submit_function(finalData)
                .finally(() => {
                    this.postInProgress = false
                })
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