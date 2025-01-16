<template>
    <div>
        <div>
            <h4 class="d-flex align-items-center">
                <i class="fas fa-plug mr-2"></i>
                Plugins
                <b-button
                    size="xs" variant ="link"
                    class="ml-auto"
                    title="Refresh plugin list"
                    @click="refreshPlugins(false)"
                >
                    <i class="fas fa-sync-alt" style="font-size: 1rem;"></i>
                </b-button>
            </h4>
        </div>

        <b-overlay :show="refreshInProgress" rounded="sm">
            <b-alert :show="noPlugin" variant="primary">
                There are no plugin available.
            </b-alert>

            <div>
                <b-badge variant="x" class="mb-2" style="border: 1px solid #bbb; background-color: #fff;">
                    <span style="color: #d22f27;" title="This fleet is marked to be monitored">
                        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24"><path fill="currentColor" d="M11 18h2v3h-2zm5 3v2H8v-2zm4-3H4a3.003 3.003 0 0 1-3-3V4a3.003 3.003 0 0 1 3-3h16a3.003 3.003 0 0 1 3 3v11a3.003 3.003 0 0 1-3 3M4 3a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1Z"/><path fill="currentColor" d="m16 15l-1.914-6.38L13 13l-1.309-3h-.331L10 14L8.843 9.933L8.309 11H5v-1h2.691L9 7l1.068 3.713L10.64 9h1.669l.487.973L14 4l2 8l.64-2H19v1h-1.64z"/></svg>
                    </span>
                    <span class="ml-1 user-select-none">Monitoring is <b-badge :variant="fleetMonitoringEnabled ? 'success' : 'danger'" style="font-size: 100%;">{{ fleetMonitoringEnabled ? 'enabled' : 'disabled' }}</b-badge></span>
                </b-badge>
            </div>

            <b-card v-if="!noPlugin" no-body>
                <b-table-simple class="mb-0">
                    <b-thead>
                        <b-tr>
                            <b-th>Enabled</b-th>
                            <b-th>Name</b-th>
                            <b-th title="Can this plugin add a column in the server index">Index</b-th>
                            <b-th title="Can this plugin add a row in the server view">View</b-th>
                            <b-th title="Can this plugin perform action on one or multiple MISP instances">Action</b-th>
                            <b-th title="Can this plugin generate entries in the server notification board">Notifications</b-th>
                        </b-tr>
                    </b-thead>
                    <b-tbody>
                        <b-tr v-for="(plugin, index) in plugins" :key="index">
                            <b-td class="text-nowrap">
                                <b-form-checkbox switch
                                    :checked="enabledPlugins.includes(plugin.id)"
                                    @change="togglePlugin(plugin.id)"
                                ></b-form-checkbox>
                            </b-td>
                            <b-td class="text-nowrap">
                                <i v-if="plugin.icon" :class="[plugin.icon, 'fa-fw mr-2']" style="width: 1rem;"></i>
                                <b>{{ plugin.name }}</b>
                                <span
                                    v-if="plugin.description"
                                    class="ml-1"
                                >
                                    <i :id="`tooltip-${index}`" class="fa fa-circle-question"></i>
                                    <b-tooltip :target="`tooltip-${index}`" triggers="hover">
                                        {{ plugin.description }}
                                    </b-tooltip>
                                </span>
                            </b-td>
                            <b-td>
                                <i
                                    :class="['fa', plugin.features.index ? 'fa-check text-success' : 'fa-times text-danger']"
                                ></i>
                            </b-td>
                            <b-td>
                                <i
                                    :class="['fa', plugin.features.view ? 'fa-check text-success' : 'fa-times text-danger']"
                                ></i>
                            </b-td>
                            <b-td>
                                <i
                                    :title="plugin.features.quickAction ? 'This plugin supports quick actions' : ''"
                                    :class="{
                                        'fa': true,
                                        'fa-check-double text-success': plugin.features.quickAction,
                                        'fa-check text-success': !plugin.features.quickAction && plugin.features.action,
                                        'fa-times text-danger': !plugin.features.quickAction && !plugin.features.action,
                                    }"
                                ></i>
                            </b-td>
                            <b-td>
                                <i
                                    :class="['fa', plugin.features.notifications ? 'fa-check text-success' : 'fa-times text-danger']"
                                ></i>
                            </b-td>
                        </b-tr>
                    </b-tbody>
                </b-table-simple>
            </b-card>
        </b-overlay>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"

export default {
    name: "PluginIndex",
    components: {
    },
    data: function () {
        return {
            refreshInProgress: false,
        }
    },
    computed: {
        ...mapGetters({
            getLoggedUserSettingByName: "userSettings/getLoggedUserSettingsByName",
            settingValues: "settings/settingValues",
            plugins: "plugins/allPlugins",
        }),
        noPlugin() {
            return this.plugins.length == 0
        },
        enabledPlugins() {
            if (this.getLoggedUserSettingByName && this.getLoggedUserSettingByName['Plugins.enabled_plugins']) {
                return this.getLoggedUserSettingByName['Plugins.enabled_plugins']
            }
            return []
        },
        fleetMonitoringEnabled() {
            return this.settingValues.monitoring_enabled || false
        },
    },
    methods: {
        refreshPlugins(use_cache) {
            this.refreshInProgress = true
            return this.$store.dispatch("plugins/getPlugins", {use_cache: use_cache})
                .catch((error) => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch plugin list",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.refreshInProgress = false
                })
        },
        togglePlugin(pluginName) {
            this.$store.dispatch('userSettings/togglePlugin', pluginName)
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: `Could not enable plugin \`${pluginName}\``,
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.refreshUserSettings()
                })
        },
        refreshUserSettings() {
            this.$store.dispatch('userSettings/getUserSettings')
            .then(() => {
                this.refreshPlugins(false)
            })
        },
    },
    mounted() {
        this.refreshUserSettings()
    }
}
</script>

<style scoped>
thead tr th {
    border-top: 0;
}
.flat-right {
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
}

.flat-left {
    border-top-left-radius: 0;
    border-bottom-left-radius: 0
}
</style>
