<template>
    <b-modal
        id="modal-settings-administration"
        :title="`Setting for server ${server.name}`"
    >
        <h5>{{ setting.setting }}:</h5>
        <b-form-checkbox
            v-if="setting.type === 'boolean'"
            v-model="setting.value"
        ></b-form-checkbox>
        <b-form-select
            v-else-if="isSelect"
            v-model="setting.value"
            :options="selectOptions"
        ></b-form-select>
        <b-form-input
            v-else
            v-model="setting.value"
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
        isSelect: function() {
            return this.setting.options !== undefined && typeof this.setting.options === "object"
        },
        inputType: function() {
            let inputType = "text"
            if (this.setting.type == "numeric") {
                inputType = "number"
            }
            return inputType
        },
        selectOptions: function() {
            let selectOptions = []
            if (this.setting.options !== undefined) {
                for (const value in this.setting.options) {
                    if (Object.hasOwnProperty.call(this.setting.options, value)) {
                        const text = this.setting.options[value]
                        selectOptions.push({text: text, value: value})
                    }
                }
            }
            return selectOptions
        }
    },
    methods: {
    },
    created: function() {
    },
    updated: function() {
    }
}
</script>