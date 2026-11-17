<template>
    <b-card no-body>
        <b-tabs v-model="activeTab" pills card vertical>
            <b-tab lazy title="Users">
                <b-card-text>
                    <userAdministration
                        :server="getServer"
                        :org-filter="userOrgFilter"
                        @clear-org-filter="userOrgFilter = null"
                    ></userAdministration>
                </b-card-text>
            </b-tab>
            <b-tab lazy title="Organisations">
                <b-card-text>
                    <orgAdministration :server="getServer" @show-users="showUsersOf"></orgAdministration>
                </b-card-text>
            </b-tab>
            <b-tab lazy title="Server Settings">
                <b-card-text>
                    <settingsAdministration :server="getServer"></settingsAdministration>
                </b-card-text>
            </b-tab>
            <b-tab lazy title="REST API">
                <b-card-text>
                    <restAPIAdministration :server="getServer"></restAPIAdministration>
                </b-card-text>
            </b-tab>
        </b-tabs>
    </b-card>
</template>

<script>
import { mapState } from "vuex"
import userAdministration from "@/views/servers/elements/mispRemoteAdministration/userAdministration.vue"
import orgAdministration from "@/views/servers/elements/mispRemoteAdministration/orgAdministration.vue"
import settingsAdministration from "@/views/servers/elements/mispRemoteAdministration/settingsAdministration.vue"
import restAPIAdministration from "@/views/servers/elements/mispRemoteAdministration/restAPIAdministration.vue"

const USERS_TAB = 0

export default {
    name: "MISPRemoteAdministration",
    components: {
        userAdministration,
        orgAdministration,
        settingsAdministration,
        restAPIAdministration,
    },
    props: {
        server_id: {
            type: Number,
            required: true
        }
    },
    data: function() {
        return {
            activeTab: USERS_TAB,
            // The organisation the Users tab is narrowed to ("Show users" of the Organisations tab)
            userOrgFilter: null,
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
        }),
        getServer: function() {
            return this.servers[this.server_id]
        },
    },
    methods: {
        showUsersOf(org) {
            this.userOrgFilter = org
            this.activeTab = USERS_TAB
        },
    }
}
</script>
