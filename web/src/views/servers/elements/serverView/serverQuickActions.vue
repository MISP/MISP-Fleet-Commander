<template>
    <div>
        <h6 class="card-header px-2 py-1">
            <div class="d-flex">
                <i class="fa fa-bolt mr-2"></i>
                <span class="my-auto">Quick Actions Panel</span>
            </div>
        </h6>
        <div class="py-1 px-2">
            <b-button-group class="mr-1">
                <b-button
                    variant="primary"
                    class="ml-auto"
                    size="sm"
                    title="Quick refresh"
                    @click="wsStatusRefresh()"
                >
                    <i class="fas fa-redo-alt"></i>
                </b-button>
                <b-button
                    :variant="getRefreshEnqueued ? 'dark' : 'primary'"
                    :disabled="getRefreshEnqueued"
                    size="sm"
                    title="Enqueue full refresh"
                    href="#"
                    @click="fullRefresh()"
                >
                    <span v-if="getRefreshEnqueued">
                        <i class="fas fa-sync-alt fa-spin"></i>
                        Refresh in progress
                    </span>
                    <span v-else>
                        <i class="fas fa-sync-alt"></i>
                        Full refresh
                    </span>
                </b-button>
            </b-button-group>

            <template v-for="plugin in quickActionPlugins">
                <b-overlay
                    v-bind:key="plugin.id"
                    :show="actionInProgressArray[plugin.id]" rounded="sm"
                    opacity="0.6"
                    spinner-small
                    class="d-inline-block"
                >
                    <b-button
                        :variant="plugin.variant"
                        size="sm"
                        class="mr-1"
                        @click="execQuickAction(plugin)"
                        :disabled="actionInProgressArray[plugin.id]"
                    >
                        <i :class="`fa fa-${plugin.icon} fa-fw mr-1`"></i>
                        <span>{{ plugin.text }}</span>
                    </b-button>
                </b-overlay>
            </template>
        </div>
    </div>
</template>

<script>
import Vue from "vue"
import { mapState, mapGetters } from "vuex"
import pluginAPI from "@/api/plugins"

export default {
    name: "ServerQuickActions",
    components: {
    },
    props: {
        server: {
            required: true,
            type: Object
        }
    },
    computed: {
        ...mapState({
            notifications: state => state.plugins.pluginNotifications,
            server_refresh_enqueued: state => state.servers.server_refresh_enqueued,
        }),
        ...mapGetters({
            quickActionPluginsRaw: "plugins/quickActionPlugins",
        }),
        quickActionPlugins: function() {
            return this.quickActionPluginsRaw.map((plugin) => {
                return {
                    id: plugin.id,
                    variant: plugin.quickActionMeta.quickActionVariant.replace('outline-', ''),
                    text: plugin.quickActionMeta.quickActionName,
                    icon: plugin.quickActionMeta.quickActionIcon,
                }
            })
        },
        getRefreshEnqueued: function() {
            return this.server_refresh_enqueued[this.server_id]
        },
    },
    data: function () {
        return {
            actionInProgressArray: {},
        }
    },
    filters: {
    },
    methods: {
        fullRefresh() {
            this.$emit("fullRefresh")
        },
        wsStatusRefresh() {
            this.$emit("wsStatusRefresh")
        },
        getToastVariant(state) {
            if (state == 'success') {
                return 'success'
            } else if (state == 'fail' || state == 'error') {
                return 'danger'
            }
            return 'primary'
        },
        execQuickAction(plugin) {
            this.actionInProgressArray[plugin.id] = true
            const form_data = {}
            pluginAPI.submitQuickAction(this.server.id, plugin.id, form_data)
                .then((response) => {
                    if (response.data.error) {
                        const errorMessage = Array.isArray(response.data.error) ? response.data.error.join(', ') : response.data.error
                        this.$bvToast.toast(errorMessage, {
                            title: `Failure while executing quick action ${plugin.text}`,
                            variant: "danger",
                        })
                    } else {
                        const successMessage = response.data.data.message
                        this.$bvToast.toast(successMessage, {
                            title: `Successfully executed quick action ${plugin.text}`,
                            variant: this.getToastVariant(response.data.status),
                        })
                    }
                })
                .catch(error => {
                    const errorMessage = error.json()
                    this.$bvToast.toast(errorMessage, {
                        title: `Could not perform quick action ${plugin.text}`,
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.actionInProgressArray[plugin.id] = false
                })
        },
    },
    mounted() {
        this.quickActionPlugins.forEach(plugin => {
            Vue.set(this.actionInProgressArray, plugin.id, false)
        });
    }
}
</script>

<style scoped>
thead tr th {
    border-top: 0;
}
</style>
