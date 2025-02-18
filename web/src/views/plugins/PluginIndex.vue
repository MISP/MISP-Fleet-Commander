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

            <div class="d-flex mb-1">
                <FleetWatchingStatusBadge class="mr-1"></FleetWatchingStatusBadge>
                <MonitoringStatusBadge></MonitoringStatusBadge>
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
import MonitoringStatusBadge from "@/components/ui/elements/MonitoringStatusBadge.vue"
import FleetWatchingStatusBadge from "@/components/ui/elements/FleetWatchingStatusBadge.vue"

export default {
    name: "PluginIndex",
    components: {
        MonitoringStatusBadge,
        FleetWatchingStatusBadge,
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
        this.refreshPlugins(false)
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
