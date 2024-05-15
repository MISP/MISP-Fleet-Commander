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
            <b-card v-if="!noPlugin" no-body>
                <b-table-simple class="mb-0">
                    <b-thead>
                        <b-tr>
                            <b-th>Enabled</b-th>
                            <b-th>Name</b-th>
                            <b-th>Index</b-th>
                            <b-th>View</b-th>
                            <b-th>Action</b-th>
                            <b-th>Notifications</b-th>
                        </b-tr>
                    </b-thead>
                    <b-tbody>
                        <b-tr v-for="(plugin, index) in plugins" :key="index">
                            <b-td class="text-nowrap">
                                <b-form-checkbox switch
                                    :checked="enabledPlugins.includes(plugin.name)"
                                    @change="togglePlugin(plugin.id)"
                                ></b-form-checkbox>
                            </b-td>
                            <b-td class="text-nowrap">
                                <i v-if="plugin.icon" :class="[plugin.icon, 'fa-fw mr-2']" style="width: 1rem;"></i>
                                <b :title="plugin.description">{{ plugin.name }}</b>
                            </b-td>
                            <b-td>
                                <i
                                    title="Can this plugin create an column in the server index"
                                    :class="['fa', plugin.features.index ? 'fa-check text-success' : 'fa-times text-danger']"
                                ></i>
                            </b-td>
                            <b-td>
                                <i
                                    title="Can this plugin create an row in the server view"
                                    :class="['fa', plugin.features.view ? 'fa-check text-success' : 'fa-times text-danger']"
                                ></i>
                            </b-td>
                            <b-td>
                                <i
                                    title="Can this plugin perform action on one or multiple MISP instances"
                                    :class="['fa', plugin.features.action ? 'fa-check text-success' : 'fa-times text-danger']"
                                ></i>
                            </b-td>
                            <b-td>
                                <i
                                    title="Can this plugin generate entries in the server notification board"
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
        ...mapState({
            plugins: state => state.plugins.all
        }),
        ...mapGetters({
            userSettings: "auth/get_user_settings",
        }),
        noPlugin() {
            return this.plugins.length == 0
        },
        enabledPlugins() {
            if (this.userSettings && this.userSettings.enabled_plugins) {
                return this.userSettings.enabled_plugins
            }
            return []
        }
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
            console.log(pluginName);
        }
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
