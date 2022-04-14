<template>
    <b-modal
        id="modal-settings-administration"
        :title="`Setting for server ${server.name}`"
    >
        <h5>{{ getSetting.setting }}:</h5>
        <b-form-checkbox
            v-if="getSetting.type === 'boolean'"
            v-model="getSetting.value"
        ></b-form-checkbox>
        <b-form-select
            v-else-if="isSelect"
            v-model="getSetting.value"
            :options="selectOptions"
        ></b-form-select>
        <b-form-input
            v-else
            v-model="getSetting.value"
            :type="inputType"
        ></b-form-input>
    </b-modal>
</template>

<script>

export default {
    name: "SettingsAdministrationModal",
    components: {
    },
    props: {
        setting: {
            required: true,
            type: Object
        },
        server: {
            required: true,
            type: Object
        },
    },
    data: function() {
        return {
            postInProgress: false,
            value: "",
        }
    },
    computed: {
        getSetting: function() {
            return {...this.setting}
        },
        isSelect: function() {
            return this.getSetting.options !== undefined && typeof this.getSetting.options === "object"
        },
        inputType: function() {
            let inputType = "text"
            if (this.getSetting.type == "numeric") {
                inputType = "number"
            }
            return inputType
        },
        selectOptions: function() {
            let selectOptions = []
            if (this.getSetting.options !== undefined) {
                for (const value in this.setting.options) {
                    if (Object.hasOwnProperty.call(this.setting.options, value)) {
                        const text = this.setting.options[value]
                        selectOptions.push({text: text, value: value})
                    }
                }
            }
            return selectOptions
        },
    },
    methods: {
    },
    created: function() {
    },
    updated: function() {
    }
}
</script>
