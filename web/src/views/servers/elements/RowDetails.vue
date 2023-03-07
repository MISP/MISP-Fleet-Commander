<template>
    <b-card no-body>
        <template v-if="getServer._loading">
            <div class="text-center text-danger my-2">
                <b-spinner class="align-middle"></b-spinner>
                <strong class="ml-2">Loading...</strong>
            </div>
        </template>
        <template v-else>
            <template v-if="getServerQueryError">
                <div class="mb-2 text-right">
                    <span class="mr-1 text-muted">
                        <i class="far fa-clock mr-1"></i>
                        <small class="align-middle">{{ getLastRefresh | moment("from") }}</small>
                    </span>
                    <b-button 
                        size="sm" variant="primary" title="Refresh"
                        @click="refreshDiagnostic()"
                    ><b-icon icon="arrow-clockwise"></b-icon></b-button>
                    <b-button 
                        size="sm" variant=""
                        @click="closeDetails()"
                    ><b-icon icon="arrow-clockwise"></b-icon></b-button>
                </div>
                <b-alert show variant="danger">
                    Error while accessing diagnostic:
                    <strong>{{ details }}</strong>
                </b-alert>
            </template>
            <template v-else>
                <b-card no-body>
                    <serverInfoAndManagements
                    :server_id="server_id"
                    @actionRefresh="$emit('actionRefresh', 'no_cache')"
                    @actionClose="$emit('actionClose', 'no_cache')"
                    ></serverInfoAndManagements>
                </b-card>
            </template>
        </template>
    </b-card>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import serverInfoAndManagements from "@/views/servers/elements/serverInfoAndManagements.vue"

export default {
    name: "RowDetails",
    components: {
        serverInfoAndManagements,
    },
    props: {
        server_id: {
            type: Number,
            required: true
        }
    },
    data: function() {
        return {
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
            server_status: state => state.servers.server_status,
            server_query_error: state => state.servers.server_query_error,
            last_refresh: state => state.servers.last_refresh,
        }),
        getServer: function() {
            return this.servers[this.server_id]
        },
        getServerStatus: function() {
            return this.server_status[this.server_id]
        },
        getLastRefresh: function() {
            return this.last_refresh[this.server_id]
        },
        getServerQueryError: function() {
            return this.server_query_error[this.server_id]
        },
    },
    methods: {
    }
}
</script>

<style scoped>
.max-heigth-700 {
    max-height: 700px;
    overflow: auto;
}
</style>
