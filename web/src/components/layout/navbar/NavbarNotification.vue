<template>
    <div>
        <b-nav-item-dropdown right>
            <template #button-content>
                <iconButton
                    style="display: inline-block !important"
                    text="Notifications"
                    icon="bell"
                    :tight="true"
                >
                    <b-badge
                        :variant="getEnquedServersForRefresh.length > 0 ? 'warning' : 'success'"
                        class="ml-1"
                        style="vertical-align: text-bottom;"
                    >{{ getEnquedServersForRefresh.length }}</b-badge>
                </iconButton>
            </template>

            <template v-if="getEnquedServersForRefresh.length > 0">
                <b-dropdown-item
                    v-for="server in getEnquedServersForRefresh"
                    v-bind:key="`notif-${server.id}`"
                >
                    <div>
                        <div>
                            <i class="fas fa-circle-notch fa-spin mr-1"></i>
                            <span class="font-weight-light">{{ server.name }}</span>
                        </div>
                        <div class="description">
                            <span class="text-secondary">Refreshing</span>
                        </div>
                    </div>
                </b-dropdown-item>
            </template>
            <template v-else>
                <b-dropdown-text>No notifications</b-dropdown-text>
            </template>

        </b-nav-item-dropdown>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import iconButton from "@/components/ui/elements/iconButton.vue"

export default {
    name: "NavbarNotification",
    components: {
        iconButton,
    },
    data: function () {
        return {
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
            server_refresh_enqueued: state => state.servers.server_refresh_enqueued,
        }),
        ...mapGetters({
           serverList: "servers/getServerList",
        }),
        getEnquedServersForRefresh() {
            return this.serverList.filter((server) => {
                return this.server_refresh_enqueued[server.id]
            })
        }
    },
    methods: {
    },
    mounted() {
    }
}
</script>

<style scoped>
.description {
    line-height: 1em;
    font-size: 0.75em;
}
</style>