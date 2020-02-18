<template>
    <b-card no-body
        v-if="open && hasSelection"
        bg-variant=""
        text-variant=""
    >
        <b-tabs card fill>
            <b-tab title="Diagnostic" no-body active>
                <b-table
                    :striped="true"
                    :bordered="false"
                    :borderless="true"
                    :outlined="false"
                    :small="true"
                    :hover="true"
                    :items="serverInfoTable"
                    :fields="fields"
                    :responsive="true"
                >
                </b-table>
            </b-tab>
            <b-tab title="Events">
                Event pic and data
            </b-tab>
            <b-tab title="Galaxies" disabled>
                Galaxy data
            </b-tab>
            <template v-slot:tabs-end>
                <b-btn-close
                    class="position-absolute close-button"
                    @click.prevent="close"
                ></b-btn-close>
            </template>
        </b-tabs>

        <template v-slot:footer>
            <small class="text-muted">Last updated 3 mins ago</small>
        </template>
    </b-card>
</template>

<script>
export default {
    name: "TheInfoSidebar",
    props: {
        server: {
            type: Object,
            required: true
        }
    },
    data: function() {
        return {
            open: true,
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
            items.push({
                property: "Name",
                value: this.server.Server.name
            })
            items.push({
                property: "URL",
                value: this.server.Server.url
            })
            items.push({
                property: "Auth key",
                value: this.server.Server.authkey
            })
            items.push({
                property: "Push",
                value: this.server.Server.push
            })
            items.push({
                property: "Pull",
                value: this.server.Server.pull
            })
            items.push({
                property: "Org. name",
                value: this.server.Organisation.name
            })
            items.push({
                property: "Org. uuid",
                value: this.server.Organisation.uuid
            })
            items.push({
                property: "Org. type",
                value: this.server.Organisation.type
            })
            return items
        },
    },
    methods: {
        close() {
            this.open = false
        }
    }
}
</script>

<style scoped>
.close-button {
    right: 4px;
    top: 0;
}
</style>