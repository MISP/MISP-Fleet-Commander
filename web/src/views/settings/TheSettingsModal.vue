<template>
    <b-modal 
        id="modal-settings"
        title="Configure Settings"
        size="xl"
        scrollable
    >
    <b-card no-body>
        <settingView
            :settings="settingByPanelsWithFullname"
            :settingValues="settingValues"
            :saveDispatcher="saveDispatcher"
            :reloadDispatcher="reloadDispatcher"
            :saveSuccessMessage="saveSuccessMessage"
        ></settingView>
    </b-card>
    </b-modal>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import settingView from "@/components/ui/SettingsView.vue"

export default {
    name: "TheSettingsModal",
    components: {
        settingView,
    },
    data: function () {
        return {
            refreshInProgress: false,
        }
    },
    computed: {
        ...mapGetters({
            getSettings: "settings/getSettings",
            settingsByPanelAndScope: "settings/settingsByPanelAndScope",
            settingValues: "settings/settingValues",
        }),
        settingByPanelsWithFullname() {
            const settingsWithFullname = JSON.parse(JSON.stringify(this.settingsByPanelAndScope))
            Object.keys(settingsWithFullname).forEach((panel) => {
                Object.keys(settingsWithFullname[panel]).forEach((scope) => {
                    Object.keys(settingsWithFullname[panel][scope]).forEach((setting_id) => {
                        settingsWithFullname[panel][scope][setting_id].full_setting_name = setting_id
                    })
                })
            })
            return settingsWithFullname
        },
    },
    methods: {
        refreshSettings() {
            this.refreshInProgress = true
            return this.$store.dispatch("settings/refreshSettings")
                .catch((error) => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch settings",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.refreshInProgress = false
                })
        },
        saveDispatcher(payload) {
            return this.$store.dispatch('settings/saveSetting', payload)
        },
        reloadDispatcher() {
            this.refreshSettings()
        },
        saveSuccessMessage(settingName) {
            return `Setting \`${settingName}\` saved`
        }
    },
    mounted() {
        this.refreshSettings()
    }
}
</script>
