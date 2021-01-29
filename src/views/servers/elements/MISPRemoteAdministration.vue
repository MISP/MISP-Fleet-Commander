<template>
    <b-card no-body>
        <b-tabs pills card vertical>
            <b-tab
                v-for="(value, scope) in administrationAction"
                v-bind:key="scope"
                :title="scope"
            >
                <b-card-text>
                    <component v-bind:is="value.component" :server="server"></component>
                </b-card-text>
            </b-tab>
        </b-tabs>
    </b-card>
</template>

<script>
import userAdministration from "@/views/servers/elements/mispRemoteAdministration/userAdministration.vue"
import orgAdministration from "@/views/servers/elements/mispRemoteAdministration/orgAdministration.vue"
import settingsAdministration from "@/views/servers/elements/mispRemoteAdministration/settingsAdministration.vue"

export default {
    name: "MISPRemoteAdministration",
    components: {
        userAdministration,
        orgAdministration,
        settingsAdministration,
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
            }
        }
    },
    computed: {
    },
    methods: {
    }
}
</script>