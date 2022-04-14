<template>
    <div>
        <b-table 
        outlined show-empty small
        table-class="table-auto-hide-action"
        table-variant="none"
        selected-variant="table-none"
        tbody-tr-class="no-outline"
        thead-tr-class="no-bgcolor"
        responsive="md"
        id="connected-servers-table"
        ref="connectedServersTable"
        :busy.sync="table.isBusy"
        :items="getIndex" 
        :fields="table.fields"
        :filterIncludedFields="table.filterFields"
        :filter="table.filter"
        :no-provider-paging="true"
        :no-provider-sorting="true"
        :no-provider-filtering="true"
        :sort-icon-left="true"
        @filtered="onFiltered"
        @sort-changed="onSorted"
        @row-clicked="rowClickHandler"
        >
            <template v-slot:table-busy>
                <div class="text-center text-danger my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong class="ml-2">Loading...</strong>
                </div>
            </template>

            <template v-slot:cell(connectionTest.status)="row">
                <connectionsSummary
                    :connections="[row.item]"
                    :row_index="row.index"
                    :text_in_badge="row.value.message"
                    :use_diode="true"
                ></connectionsSummary>
            </template>

        </b-table>
    </div>
</template>

<script>
import connectionsSummary from "@/views/servers/elements/connectionsSummary.vue"

export default {
    name: "MISPConnectedServers",
    components: {
        connectionsSummary
    },
    props: {
        servers: {
            type: Object,
            required: true
        }
    },
    data: function() {
        return {
            table: {
                isBusy: false,
                filtered: "",
                totalRows: 0,
                currentPage: 1,
                perPage: 30,
                optionsPerPage: [{ text: 30, value: 30 }, { text: 50, value: 50 }, { text: 100, value: 100 }],
                filterFields: [""],
                fields: [
                    {
                        key: "Server.name",
                        label: "Name",
                        sortable: true
                    },
                    {
                        key: "Server.url",
                        label: "URL",
                        sortable: true
                    },
                    {
                        key: "Server.push",
                        label: "Push",
                        sortable: true,
                    },
                    {
                        key: "Server.pull",
                        label: "Pull",
                        sortable: true,
                    },
                    {
                        key: "connectionTest.status",
                        label: "Status",
                        sortable: true,
                        tdClass: "align-middle"
                    },
                ],
            },
        }
    },
    computed: {
        getIndex() {
            return Object.values(this.servers)
        },
    },
    methods: {
        onFiltered(filteredItems) {
            this.table.totalRows = filteredItems.length
            this.table.currentPage = 1
        },
        onSorted() {
            this.table.currentPage = 1
        },
        rowClickHandler(item) {
            this.selectedItem = item
            this.$nextTick(() => {
                this.$bvModal.show("modal-user-administration")
            })
        },
    }
}
</script>
