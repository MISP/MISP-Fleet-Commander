<template>
    <div class="nodeServer">
        <b-card 
            header-tag="header"
            header-bg-variant="primary"
            header-text-variant="white"
            border-variant="primary"
            footer-tag="footer"
        >
            <template v-slot:header>
                <div class="d-flex justify-content-between">
                    <b>{{ server.Server.name }}</b>
                    <i><small>{{ server.Server.url }}</small></i>
                </div>
            </template>
            
            {{ server.RemoteOrg.name }} > {{ server.Server.org_id }}
        </b-card>
    </div>
</template>

<script>
export default {
    name: "Node",
    components: {
    },
    data: function () {
        return {
        }
    },
    computed: {
    },
    methods: {
    },
    props: {
        event: {
            type: Object,
            required: true
        },
        server: {
            type: Object,
            required: true
        }
    }
}
</script>

<style scoped>
.nodeServer {
    height: 100%
}

.nodeServer > div.card {
    height: 100%
}

.nodeServer > div.card > div.card-body {
    flex-grow: 1;
}
</style>