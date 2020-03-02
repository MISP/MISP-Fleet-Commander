<template>
<Layout name="LayoutDefault">
    <div>
        <h3>
            <iconForScope scope="connections"></iconForScope>
            Connections
        </h3>

        <div class="d-flex justify-content-between">
            <div>
                <b-pagination
                    v-model="table.currentPage"
                    v-if="table.totalRows > table.perPage"
                    :per-page="table.perPage"
                    :total-rows="table.totalRows"
                    aria-controls="server-table"
                ></b-pagination>
            </div>
            <div class="align-items-center d-flex w-25">
                <b-input-group size="sm">
                    <b-form-input
                        v-model="table.filter"
                        type="search"
                        id="filterInput"
                        placeholder="Type to Search"
                        class="border-bottom-0 rounded-top align-self-end"
                        style="border-radius: 0"
                    ></b-form-input>
                </b-input-group>
                <b-button class="ml-2" variant="primary" size="sm" @click="refreshConnections()">
                    <b-icon icon="arrow-clockwise" :class="{'fa-spin': refreshInProgress}" title="Refresh Servers"></b-icon>
                </b-button>
           </div>
        </div>

        <b-table 
            striped outlined hover show-empty small
            responsive="md"
            id="connection-table"
            ref="connectionTable"
            :per-page="table.perPage"
            :current-page="table.currentPage"
            :busy.sync="table.isBusy"
            :items="getConnections" 
            :fields="table.fields"
            :filterIncludedFields="table.filterFields"
            :filter="table.filter"
            :no-provider-paging="true"
            :no-provider-sorting="true"
            :no-provider-filtering="true"
            @filtered="onFiltered"
            @sort-changed="onSorted"
        >
            <template v-slot:table-busy>
                <div class="text-center text-danger my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong class="ml-2">Loading...</strong>
                </div>
            </template>

            <template v-slot:cell(source)="row">
                <span>{{ row.value.name }} </span>
                <small><b-link :href="row.value.url" target="_blank">{{ row.value.url }} <sup class="fa fa-external-link-alt"></sup></b-link></small>
            </template>

            <template v-slot:cell(destination)="row">
                <span>{{ row.value.Server !== undefined ? row.value.Server.name : '' }} </span>
                <small>
                    <b-link :href="row.value.Server !== undefined ? row.value.Server.url : '#'" target="_blank">
                        {{ row.value.Server !== undefined ? row.value.Server.url : '' }} <sup class="fa fa-external-link-alt"></sup>
                    </b-link>
                </small>
            </template>

            <template v-slot:cell(status)="row">
                <loaderPlaceholder :loading="!row.value._loading">
                    <connectionsSummary
                        :connections="[row.item.destination]"
                        :row_index="row.index"
                        :text_in_badge="row.value.status.message"
                    ></connectionsSummary>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(pull)="row">
                <loaderPlaceholder :loading="!row.value._loading">
                    <b-button :id="`pull-rule-${row.index}`" variant="link" size="xs" class="m-0 text-dark" href="#" tabindex="0">
                        <i
                            :class="['method-status', 'fa', row.value ? 'fa-check' : 'fa-times']"
                        ></i>
                        <small>
                            ({{ row.item.filtering_rules.pull_rule_number }} pull rules)
                        </small>
                    </b-button>
                    <b-popover
                        :target="`pull-rule-${row.index}`"
                        triggers="focus"
                        title="Pull rules"
                    >
                        <template v-slot:title>
                            <div class="d-flex">
                                <span>Pull rules</span>
                                <b-button variant="link" size="sm" class="ml-auto p-0 m-0"
                                    @click="toggleRulesTreeMode"
                                >
                                    <i :class="['fas', rulesTreeMode ? 'fa-code' : 'fa-stream']"></i>
                                </b-button>
                            </div>
                        </template>
                        <jsonViewer 
                            :tree="rulesTreeMode"
                            :item="row.item.filtering_rules.pull_rules"
                            rootKeyName="Pull rules"
                            :open="true"
                        ></jsonViewer>
                    </b-popover>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(push)="row">
                <loaderPlaceholder :loading="!row.value._loading">
                    <b-button :id="`push-rule-${row.index}`" variant="link" size="xs" class="m-0 text-dark" href="#" tabindex="0">
                        <i 
                            :id="`push-rule-${row.index}`"
                            :class="['method-status', 'fa', row.value ? 'fa-check' : 'fa-times']"
                        ></i>
                        <small>
                            ({{ row.item.filtering_rules.push_rule_number }} push rules)
                        </small>
                    </b-button>
                    <b-popover
                        :target="`push-rule-${row.index}`"
                        triggers="focus"
                        title="Push rules"
                    >
                        <template v-slot:title>
                            <div class="d-flex">
                                <span>Push rules</span>
                                <b-button variant="link" size="sm" class="ml-auto p-0 m-0"
                                    @click="toggleRulesTreeMode"
                                >
                                    <i :class="['fas', rulesTreeMode ? 'fa-code' : 'fa-stream']"></i>
                                </b-button>
                            </div>
                        </template>
                        <jsonViewer
                            :tree="rulesTreeMode"
                            :item="row.item.filtering_rules.push_rules"
                            rootKeyName="Push rules"
                            :open="true"
                        ></jsonViewer>
                    </b-popover>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(last_refresh)="row">
                <loaderPlaceholder :loading="!row.value._loading">
                    <timeSinceRefresh
                        :timestamp="row.value"
                    ></timeSinceRefresh>
                </loaderPlaceholder>
            </template>

            <template v-slot:row-details="row">
                <RowDetails 
                    :details="row.item"
                    :server="row.item"
                ></RowDetails>
            </template>

        </b-table>
    </div>
</Layout>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import Layout from "@/components/layout/Layout.vue"
import iconForScope from "@/components/ui/elements/iconForScope.vue"
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"
import userPerms from "@/components/ui/elements/userPerms.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import connectionsSummary from "@/components/ui/elements/connectionsSummary.vue"
import connectionState from "@/components/ui/elements/connectionState.vue"
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"

export default {
    name: "TheConnections",
    components: {
        Layout,
        iconForScope,
        loaderPlaceholder,
        timeSinceRefresh,
        jsonViewer,
        connectionsSummary
    },
    data: function () {
        return {
            refreshInProgress: false,
            rulesTreeMode: true,
            table: {
                isBusy: false,
                filtered: "",
                totalRows: 0,
                currentPage: 1,
                perPage: 30,
                filterFields: ["source", "destination"],
                fields: [
                    {
                        key: "source",
                        sortable: true
                    },
                    {
                        key: "destination",
                        sortable: true,
                    },
                    {
                        key: "status",
                        label: "Status",
                        sortable: true,
                        tdClass: "align-middle"
                    },
                    {
                        key: "pull",
                        sortable: true
                    },
                    {
                        key: "push",
                        sortable: true
                    },
                    {
                        key: "last_refresh",
                        sortable: true,
                        class: "align-middle"
                    },
                    {
                        key: "actions",
                        class: "align-middle d-none d-md-table-cell",
                    }
                ]
            }
        }
    },
    computed: {
        ...mapState({
            getConnections: state => state.connections.all
        }),
    },
    methods: {
        onFiltered(filteredItems) {
            this.table.totalRows = filteredItems.length
            this.table.currentPage = 1
        },
        onSorted() {
            this.table.currentPage = 1
        },
        refreshConnections() {
            this.refreshInProgress = true
            this.$store.dispatch("connections/getConnections")
                .then(() => {
                    this.table.totalRows = this.serverCount
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch connection index",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.refreshInProgress = false
                })
        },
        toggleRulesTreeMode() {
            this.rulesTreeMode = !this.rulesTreeMode
        }
    },
    mounted() {
        this.refreshConnections()
    }
}
</script>

<style scoped>
    .method-status {
        width: 14px;
    }
</style>
