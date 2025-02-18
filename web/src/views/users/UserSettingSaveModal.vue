<template>
    <b-modal
        id="user-setting-modal"
        ref="user-setting-modal"
        size="xl"
        ok-only
        ok-title="Close"
    >
        <template #modal-title>
            <h5>
                Edit user settings of <span class="preFontStyle">{{ selectedUser.email }}</span>
            </h5>
        </template>
        <b-card
            no-body
            class="mb-2"
            header-class="font-weight-bold"
        >
            <b-tabs
                pills card vertical
                content-class="p-3"
            >
                <b-tab
                    v-for="(panelSettings, panel, i) in allUserSettings" :key="panel"
                    :title="panel"
                    :active="i == 0"
                    no-body
                >
                    <div style="min-height: 25vh">
                        <h4>{{ panel }}</h4>
                        <b-table-simple small bordered striped class="mb-0">
                            <b-tbody>
                                <b-tr v-for="setting in panelSettings" :key="setting.name">
                                    <b-td style="width: 0%;">
                                        <span class="d-flex flex-column">
                                            <strong>{{ setting.text ? setting.text : setting.name }}</strong>
                                            <code><small>{{ setting.full_setting_name }}</small></code>
                                        </span>
                                    </b-td>
                                    <b-td class="align-middle">
                                        <formInputFromConfig
                                            :type="setting.type"
                                            :input_key="setting.full_setting_name"
                                            :user_value="selectedUserSettingsByName[setting.full_setting_name]"
                                            :params="setting"
                                            @input="handleInputChange"
                                        >
                                        </formInputFromConfig>
                                    </b-td>
                                    <b-td class="align-middle" style="width: 0%;">
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
                </b-tab>
            </b-tabs>

        </b-card>
    </b-modal>
</template>

<script>
import { mapGetters } from "vuex"
import formInputFromConfig from "@/components/ui/elements/formInputFromConfig.vue"

export default {
    name: "UserSettingSaveModal",
    components: {
        formInputFromConfig,
    },
    props: {
        selectedUser: {
        },
    },
    data: function() {
        return {
            postInProgress: {},
            changedSettings: {},
            lastupdate: null,
            backupOriginalSettings: {},
        }
    },
    computed: {
        ...mapGetters({
            allUserSettings: "userSettings/getAllUserSettings",
            allUserSettingsName: "userSettings/getAllUserSettingsName",
        }),
        userEmail() {
            return this.selectedUser ? this.selectedUser.email : '?'
        },
        selectedUserSettingsByName() {
            let settingsByName = {}
            if (this.allUserSettingsName.length > 0) {
                this.allUserSettingsName.forEach(settingName => {
                    settingsByName[settingName] = ''
                })
                if (this.selectedUser?.user_settings !== undefined) {
                    this.selectedUser.user_settings.forEach(setting => {
                        settingsByName[setting.name] = setting.value
                    })
                }
                Object.keys(this.changedSettings).forEach((settingName => {
                    settingsByName[settingName] = this.changedSettings[settingName]
                }))
            }
            return settingsByName
        }
    },
    methods: {
        backupSettings() {
            this.backupOriginalSettings = JSON.parse(JSON.stringify(this.selectedUserSettingsByName))
        },
        handleInputChange(input_key, value) {
            if (this.changedSettings[input_key] != value) {
                this.$set(this.changedSettings, input_key, value)
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
                user_id: this.selectedUser.id
            }
            this.$store.dispatch('userSettings/editForUser', payload)
                .then(() => {
                    this.$bvToast.toast(`User setting \`${this.settingName}\` for user \`${this.selectedUser.email}\` saved`, {
                        title: "User setting successfully saved",
                        variant: "success",
                    })
                    this.$emit("save-success", "done")
                    this.backupOriginalSettings[settingName] = this.changedSettings[settingName]
                    this.reloadSettings()
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: `Could not save user setting \`${this.settingName}\``,
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.$set(this.postInProgress, settingName, false)
                })
        },
        resetSetting(settingName) {
            this.changedSettings[settingName] = this.backupOriginalSettings[settingName]
        },
        reloadSettings() {
            this.$store.dispatch('userSettings/getUserSettings')
        }
    },
    mounted() {
    },
    watch: {
        selectedUser: function() {
            this.backupSettings()
        }
    }
}
</script>

<style scoped>
.preFontStyle {
    font-size: 87.5%;
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}
</style>