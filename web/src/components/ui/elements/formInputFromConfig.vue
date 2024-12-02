<template>
    <b-form-select
        v-if="type == 'select'"
        v-model="formData[input_key]"
        :options="params.options"
        @input="emitInput(input_key, formData[input_key])"
    >
        <template #first>
            <b-form-select-option :value="null" disabled>-- Please select an option --</b-form-select-option>
        </template>
    </b-form-select>

    <b-form-checkbox
        v-else-if="type == 'checkbox'"
        :key="`${input_key}`"
        v-model="formData[input_key]"
        @input="emitInput(input_key, formData[input_key])"
    >{{ params.text }}</b-form-checkbox>

    <b-form-textarea
        v-else-if="type == 'textarea'"
        v-model="formData[input_key]"
        :type="type"
        :placeholder="params.placeholder || ''"
        rows="3"
        max-rows="6"
        @input="emitInput(input_key, formData[input_key])"
    ></b-form-textarea>

    <selectPicker
        v-else-if="type == 'picker'"
        @input="(value) => { handleInput(input_key, value) }"
        :value="formData[input_key]"
        :options="params.options"
    ></selectPicker>

    <b-form-input
        v-else
        v-model="formData[input_key]"
        v-bind="validProps()"
        :type="inputType"
        :placeholder="params.placeholder || ''"
        @input="emitInput(input_key, formData[input_key])"
    ></b-form-input>
</template>

<script>
import Vue from "vue"
import selectPicker from "@/components/ui/pluginElements/selectPicker.vue"


export default {
    name: "formInputFromConfig",
    components: {
        selectPicker,
    },
    props: {
        type: {
            type: String,
            required: true,
        },
        input_key: {
            type: String,
            required: true,
        },
        user_value: {
        },
        params: {
            type: Object,
            required: true,
        }
    },
    data: function () {
        return {
            formData: {},
        }
    },
    computed: {
        valueCasted() {
            if (this.type == 'checkbox' && typeof this.user_value === 'string') {
                return this.user_value === '1'
            } else if (this.type == 'picker' && !Array.isArray(this.user_value)) {
                return []
            }
            return this.user_value
        },
        inputType() {
            const valid_types = ['color', 'date', 'datetime-local', 'email', 'number', 'password', 'url', ]
            if (valid_types.includes(this.type)) {
                return this.type
            }
            return 'text'
        }
    },
    methods: {
        handleInput: function(formKey, value) {
            this.formData[formKey] = value
            this.emitInput(this.input_key, this.formData[this.input_key])
        },
        emitInput: function(input_key, value) {
            this.$emit('input', input_key, value)
        },
        validProps: function() {
            const accepted_props = ['min', 'max', 'step', 'pattern', 'value', 'placeholder']
            const valid_props = {}
            accepted_props.forEach((propName) => {
                if (this.params[propName] !== undefined) {
                    valid_props[propName] = this.params[propName]
                }
            })
            return valid_props
        }
    },
    created() {
        Vue.set(this.formData, this.input_key, this.valueCasted)
        // if (this.type == 'picker') {
        //     Vue.set(this.formData, this.input_key, [])
        // } else {
        //     Vue.set(this.formData, this.input_key, null)
        // }
    },
    watch: {
        user_value: function() {
            this.formData[this.input_key] = this.valueCasted
        }
    }
}
</script>