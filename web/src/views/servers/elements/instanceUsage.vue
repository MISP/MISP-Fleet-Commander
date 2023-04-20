<template>
    <b-card no-body>
        <b-tabs pills card vertical>
            <b-tab lazy no-body
                title="Usage graph"
            >
                Some graphs
            </b-tab>

            <b-tab lazy no-body
                title="Usage basic stats"
            >
                <b-table-simple
                    striped small
                    class="mb-0"
                    :bordered="false"
                    :borderless="true"
                    :outlined="false"
                >
                    <b-tbody>
                        <b-tr v-for="(v, k) in getServerUsage.stats" v-bind:key="k">
                            <b-th>{{ k }}</b-th>
                            <b-td>{{ v }}</b-td>
                        </b-tr>
                    </b-tbody>
                </b-table-simple>
            </b-tab>
        </b-tabs>
    </b-card>
</template>

<script>
import { mapState, mapGetters } from "vuex"

export default {
    name: "instanceUsage",
    components: {
    },
    props: {
        server_id: {
            required: true,
            type: Number,
        },
    },
    data: function () {
        return {
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
            server_usage: state => state.servers.server_usage,
            server_publication_activity: state => state.servers.server_publication_activity,
            last_refresh: state => state.servers.last_refresh,
        }),
        getServer: function () {
            return this.servers[this.server_id]
        },
        getServerUsage: function () {
            return this.server_usage[this.server_id]
        },
        getServerPublicationActivity: function () {
            return this.server_publication_activity[this.server_id]
        },
    },
    methods: {
    }
}
</script>

<style scoped>

</style>