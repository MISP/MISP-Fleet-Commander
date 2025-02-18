<template>
<div>
    <b-tabs
        pills card vertical
        content-class="p-3"
    >
        <b-tab
            v-for="(panelSettings, panel, i) in settings" :key="panel"
            :title="panel"
            :active="i == 0"
            no-body
        >
            <div style="min-height: 25vh">
                <div
                    v-for="(scopeSettings, scope) in panelSettings" :key="scope"
                    class="mb-3"
                >
                    <h4 class="border-bottom">{{ scope | capitalize }}</h4>
                    <b-table-simple small class="mb-0" fixed borderless>
                        <b-tbody>
                            <b-tr v-for="setting in scopeSettings" :key="setting.name">
                                <b-td>
                                    <span class="d-inline-flex flex-column">
                                        <strong>{{ setting.text ? setting.text : setting.name }}</strong>
                                        <code><small>{{ setting.full_setting_name }}</small></code>
                                        <small class="text-muted">{{ setting.description }}</small>
                                    </span>
                                </b-td>
                                <b-td class="align-middle p-2" style="width: 520px;">
                                    <formInputFromConfig
                                        :type="setting.type"
                                        :input_key="setting.full_setting_name"
                                        :user_value="selfSettingValues[setting.full_setting_name]"
                                        :params="setting"
                                        @input="handleInputChange"
                                    >
                                    </formInputFromConfig>
                                </b-td>
                                <b-td class="align-middle p-2" style="width: 100px;">
                                    <b-button-group size="sm">
                                        <b-button
                                            :variant="changePending(setting.full_setting_name) ? 'success' : 'outline-secondary'"
                                            :disabled="!changePending(setting.full_setting_name) || postInProgress[setting.full_setting_name]"
                                            :title="!changePending(setting.full_setting_name) || postInProgress[setting.full_setting_name] ? 'There is nothing save.' : ''"
                                            :lastupdate="lastupdate"
                                            @click="saveSetting(setting.full_setting_name)"
                                        >
                                            <b-spinner 
                                                small
                                                v-if="postInProgress[setting.full_setting_name]"
                                            ></b-spinner>
                                            <span class="sr-only">Saving...</span>
                                            <span v-if="!postInProgress[setting.full_setting_name]">Save</span>
                                        </b-button>
                                        <b-button
                                            :variant="changePending(setting.full_setting_name) ? 'outline-secondary' : 'outline-secondary'"
                                            :disabled="!changePending(setting.full_setting_name) || postInProgress[setting.full_setting_name]" :lastupdate="lastupdate"
                                            @click="resetSetting(setting.full_setting_name)"
                                            class="d-flex align-items-center"
                                        ><i class="fa fa-times"></i></b-button>
                                    </b-button-group>
                                </b-td>
                            </b-tr>
                        </b-tbody>
                    </b-table-simple>
                </div>
            </div>
        </b-tab>
    </b-tabs>
</div>
</template>

<script>
import formInputFromConfig from "@/components/ui/elements/formInputFromConfig.vue"


export default {
    name: "SettingsView",
    components: {
        formInputFromConfig,
    },
    props: {
        settings: {
            type: Object,
            required: true,
        },
        settingValues: {
            type: Object,
            required: true,
        },
        saveDispatcher: {
            type: Function,
            required: true,
        },
        reloadDispatcher: {
            type: Function,
            required: true,
        },
        saveSuccessMessage: {
            type: Function,
            required: true,
        },

    },
    data: function() {
        return {
            selfSettingValues: JSON.parse(JSON.stringify(this.settingValues)),
            postInProgress: {},
            changedSettings: {},
            lastupdate: null,
            backupOriginalSettings: {},
        }
    },
    computed: {
    },
    filters: {
        capitalize: function (value) {
            if (!value) return ''
            value = value.toString()
            return value.charAt(0).toUpperCase() + value.slice(1)
        }
    },
    methods: {
        backupSettings() {
            this.backupOriginalSettings = JSON.parse(JSON.stringify(this.settingValues))
        },
        handleInputChange(input_key, value) {
            if (this.changedSettings[input_key] != value) {
                this.$set(this.changedSettings, input_key, value)
                this.selfSettingValues[input_key] = value
                this.lastupdate = Date()
            }
        },
        changePending(settingName) {
            return this.changedSettings[settingName] !== undefined && this.changedSettings[settingName] !== this.backupOriginalSettings[settingName]
        },
        saveSetting(settingName) {
            this.$set(this.postInProgress, settingName, true)
            const payload = {
                name: settingName,
                value: this.changedSettings[settingName],
            }
            this.saveDispatcher(payload)
                .then(() => {
                    const successMessage = this.saveSuccessMessage(settingName)
                    this.$bvToast.toast(successMessage, {
                        title: "Setting successfully saved",
                        variant: "success",
                    })
                    this.$emit("save-success", "done")
                    this.reloadSettings()
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: `Could not save setting \`${this.settingName}\``,
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.$set(this.postInProgress, settingName, false)
                })
        },
        resetSetting(settingName) {
            this.changedSettings[settingName] = this.backupOriginalSettings[settingName]
            this.selfSettingValues[settingName] = this.backupOriginalSettings[settingName]
        },
        reloadSettings() {
            this.reloadDispatcher()
        },
    },
    mounted() {
        this.backupSettings()
    },
    watch: {
        settingValues: function() {
            this.backupSettings()
        }
    }
}
</script>