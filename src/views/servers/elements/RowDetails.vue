<template>
    <b-card no-body>
        <template v-if="server._loading">
            <div class="text-center text-danger my-2">
                <b-spinner class="align-middle"></b-spinner>
                <strong class="ml-2">Loading...</strong>
            </div>
        </template>
        <template v-else>
            <template v-if="details.error">
                <div class="mb-2 text-right">
                    <span class="mr-1 text-muted">
                        <i class="far fa-clock mr-1"></i>
                        <small class="align-middle">{{ details.query_result.timestamp | moment("from") }}</small>
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
                    :server="server"
                    :server_info="details"
                    @actionRefresh="$emit('actionRefresh', 'no_cache')"
                    @actionClose="$emit('actionClose', 'no_cache')"
                    ></serverInfoAndManagements>
                </b-card>
            </template>
        </template>
    </b-card>
</template>

<script>
import serverInfoAndManagements from "@/views/servers/elements/serverInfoAndManagements.vue"

export default {
    name: "RowDetails",
    components: {
        serverInfoAndManagements,
    },
    props: {
        details: {
            type: Object,
            required: true
        },
        server: {
            type: Object,
            required: true
        }
    },
    data: function() {
        return {
        }
    },
    computed: {
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