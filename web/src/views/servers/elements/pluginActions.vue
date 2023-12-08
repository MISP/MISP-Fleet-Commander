<template>
    <b-card no-body>
        <b-tabs pills card vertical>
            <b-tab
                v-for="plugin in actionPlugins"
                v-bind:key="plugin.id"
                :title="plugin.name"
                lazy
            >
                <template #title>
                    <i v-if="plugin.icon" :class="[plugin.icon, 'fa-fw mr-1']" style="width: 1rem;"></i>
                    {{ plugin.name }}
                </template>
                <div>
                    <pluginAction
                        :server_id="server_id"
                        :plugin="plugin"
                    ></pluginAction>
                </div>
            </b-tab>
        </b-tabs>
    </b-card>
</template>

<script>
import { mapGetters } from "vuex"
import pluginAction from "@/views/servers/elements/pluginAction.vue"

export default {
    name: "pluginActions",
    components: {
        pluginAction,
    },
    props: {
        server_id: {
            type: Number,
            required: true
        },
    },
    data: function() {
        return {
        }
    },
    computed: {
        ...mapGetters({
            actionPlugins: "plugins/actionPlugins",
        }),
    },
    methods: {
    },
}
</script>

<style scoped>

</style>