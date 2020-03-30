<template>
    <b-card no-body
        v-show="open && (hasSelection || true)"
        bg-variant=""
        text-variant=""
        id="networkInfoPanel"
    >
        <b-tabs
            card fill small
        >
            <b-tab title="Info" no-body active>
                <b-table
                    striped small
                    class="mb-0"
                    :bordered="false"
                    :borderless="true"
                    :outlined="false"
                    :items="serverInfoTable"
                    :fields="fields"
                >
                </b-table>
            </b-tab>
            <b-tab title="Diagnostic">
                Diagnostic
            </b-tab>
            <b-tab title="Content">
                Event pic and data
            </b-tab>
            <template v-slot:tabs-end>
                <b-btn-close
                    class="position-absolute close-button"
                    @click.prevent="close"
                ></b-btn-close>
            </template>
        </b-tabs>

        <template v-slot:footer>
            <timeSinceRefresh
                v-if="server.status"
                :key="server.id"
                :timestamp="server.status.timestamp"
            ></timeSinceRefresh>
            <!-- <timeSinceRefresh
                :timestamp="server.server_info.query_result.timestamp"
            ></timeSinceRefresh> -->
        </template>
    </b-card>
</template>

<script>
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"

export default {
    name: "TheInfoCard",
    components: {
        timeSinceRefresh
    },
    props: {
        server: {
            type: Object,
            required: true
        },
        open: {
            type: Boolean,
            required: true
        },
    },
    data: function() {
        return {
            fields: [
                { key: "property", thStyle: { display: "none" } },
                { key: "value", thStyle: { display: "none" } }
            ]
        }
    },
    computed: {
        hasSelection() {
            return Object.keys(this.server).length > 0
        },
        serverInfoTable() {
            let items = []
            items = items.concat([
                {
                    property: "Name",
                    value: this.server.name
                },
                {
                    property: "URL",
                    value: this.server.url
                },
                {
                    property: "Auth key",
                    value: this.server.authkey
                }
            ])
            if (
                this.server.server_info !== undefined &&
                this.server.server_info.query_result.serverUser.Organisation !== undefined
            ) {
                items = items.concat([
                    {
                        property: "Org. name",
                        value: this.server.server_info.query_result.serverUser.Organisation.name
                    },
                    {
                        property: "Org. uuid",
                        value: this.server.server_info.query_result.serverUser.Organisation.uuid
                    },
                    {
                        property: "Org. type",
                        value: this.server.server_info.query_result.serverUser.Organisation.type
                    }
                ])
            } else {
                items = items.concat([
                    {
                        property: "Org. name",
                        value: ""
                    },
                    {
                        property: "Org. uuid",
                        value: ""
                    },
                    {
                        property: "Org. type",
                        value: ""
                    }
                ])
            }
            return items
        },
    },
    methods: {
        close() {
            this.$emit("update:open", false)
        },
    }
}
</script>

<style scoped>
    .close-button {
        right: 4px;
        top: 0;
        user-select: none;
    }
</style>

<style>
    .right-panel {
        z-index: 2;
    }

    .right-panel .card-header {
        padding: 0.5rem 0.5rem;
        cursor: move;
    }
    
    .right-panel .card-header > ul.card-header-tabs {
        margin-left: 0;
        margin-right: 0;
        margin-bottom: -0.5rem;
    }
    
    .right-panel .card-header > ul.card-header-tabs > li.nav-item {
    
    }
    
    .right-panel .card-header > ul.card-header-tabs > li.nav-item > a.nav-link {
        padding: 0.3rem 0;
        user-select: none;
    }
    
    .right-panel .card-footer {
        padding: 0.2rem 1rem;
    }

    .right-panel table {
        font-size: 0.7rem;
    }
</style>