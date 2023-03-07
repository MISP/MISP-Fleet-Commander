<template>
    <b-card no-body>
        <b-tabs pills card vertical>
            <b-tab lazy
                v-for="(value, scope) in administrationAction"
                v-bind:key="scope"
                :title="scope"
            >
                <b-card-text>
                    <component v-bind:is="value.component" :server="getServer" lazy></component>
                </b-card-text>
            </b-tab>
        </b-tabs>
    </b-card>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import userAdministration from "@/views/servers/elements/mispRemoteAdministration/userAdministration.vue"
import orgAdministration from "@/views/servers/elements/mispRemoteAdministration/orgAdministration.vue"
import settingsAdministration from "@/views/servers/elements/mispRemoteAdministration/settingsAdministration.vue"
import restAPIAdministration from "@/views/servers/elements/mispRemoteAdministration/restAPIAdministration.vue"

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
            administrationAction: {
                Users: { component: "userAdministration" },
                Organisation: { component: "orgAdministration" },
                "Server Settings": { component: "settingsAdministration" },
                "REST API": {component: "restAPIAdministration"}
            }
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
    }
}
</script>
