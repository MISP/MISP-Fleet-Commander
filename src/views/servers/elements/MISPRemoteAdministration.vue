<template>
    <b-card no-body>
        <b-tabs pills card vertical>
            <b-tab
                v-for="(value, scope) in administrationAction"
                v-bind:key="scope"
                :title="scope"
            >
                <b-card-text>
                    <keep-alive>
                        <component v-bind:is="value.component" :server="server"></component>
                    </keep-alive>
                </b-card-text>
            </b-tab>
        </b-tabs>
    </b-card>
</template>

<script>
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
        server: {
            type: Object,
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
    },
    methods: {
    }
}
</script>