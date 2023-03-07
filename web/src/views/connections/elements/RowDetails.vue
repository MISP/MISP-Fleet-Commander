<template>
    <b-card no-body>
        <template v-if="connection._loading">
            <div class="text-center text-danger my-2">
                <b-spinner class="align-middle"></b-spinner>
                <strong class="ml-2">Loading...</strong>
            </div>
        </template>
        <template v-else>
            <template v-if="connection.error">
                <div class="mb-2 text-right">
                    <span class="mr-1 text-muted">
                        <i class="far fa-clock mr-1"></i>
                        <small class="align-middle">{{ getDetails.query_result.timestamp | moment("from") }}</small>
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
                    Error while accessing details:
                    <strong>{{ getDetails }}</strong>
                </b-alert>
            </template>
            <template v-else>
                <b-card no-body>
                    <b-tabs card>
                        <b-tab class="p-1" no-body>
                            <template #title>
                                <i class="fas fa-tools mr-1"></i><strong>Remote administration</strong>
                            </template>
                            <div class="max-heigth-700">
                                administration
                            </div>
                        </b-tab>
                        <b-tab title="Diagnostic" class="p-1" active no-body>
                            <b-card no-body>
                                <b-tabs pills card vertical>
                                    <b-tab
                                        v-for="(value, setting) in getDetails"
                                        v-bind:key="setting"
                                        :title="setting"
                                    >
                                        <b-card-text>
                                            <div class="max-heigth-700">
                                                <MISPSchemaDiagnostic
                                                    v-if="setting == 'dbSchemaDiagnostics'"
                                                    :schemaDiagnostic="value"
                                                ></MISPSchemaDiagnostic>
                                                <b-table
                                                    v-else-if="isTabularView(setting)"
                                                    striped
                                                    table-class="table-no-select"
                                                    :fields="fieldsFromObject(value[0])"
                                                    :items="value"
                                                ></b-table>
                                                <b-table-simple
                                                    v-else-if="isListView(setting)"
                                                    striped small
                                                    class="mb-0"
                                                    :bordered="false"
                                                    :borderless="true"
                                                    :outlined="false"
                                                >
                                                    <b-tbody>
                                                        <b-tr v-for="(v, k) in value" v-bind:key="k">
                                                            <b-th>{{ k }}</b-th>
                                                            <b-td>{{ v }}</b-td>
                                                        </b-tr>
                                                    </b-tbody>
                                                </b-table-simple>
                                                <jsonViewer
                                                    v-else
                                                    :item="value"
                                                    :rootKeyName="setting"
                                                    :open="true"
                                                ></jsonViewer>
                                            </div>
                                        </b-card-text>
                                    </b-tab>
                                </b-tabs>
                            </b-card>
                        </b-tab>
                        <b-tab title="Activity" no-body>
                            <b-card no-body>
                                <div class="max-heigth-700">
                                    <jsonViewer
                                        :item="getDetails"
                                        rootKeyName="Usage"
                                        :open="true"
                                    ></jsonViewer>
                                </div>
                            </b-card>
                        </b-tab>

                        <template v-slot:tabs-end>
                            <b-nav-item href="#" class="ml-auto rightmost-action">
                                <timeSinceRefresh
                                    :timestamp="connection.last_refresh"
                                    type="ddd DD/MM/YYYY HH:mm"
                                ></timeSinceRefresh>
                                <b-button variant="primary" size="sm" @click="refreshDiagnostic()">
                                    <iconButton
                                        text="Refresh"
                                        icon="sync-alt"
                                        :tight="true"
                                    ></iconButton>
                                </b-button>
                                <b-button class="ml-1 darken-on-hover" size="xs" variant="link" @click="closeDetails()">
                                    <i class="fas fa-times"></i>
                                </b-button>
                            </b-nav-item>
                        </template>
                    </b-tabs>
                </b-card>
            </template>
        </template>
    </b-card>
</template>

<script>
import iconButton from "@/components/ui/elements/iconButton.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"
import MISPSchemaDiagnostic from "@/views/servers/elements/MISPSchemaDiagnostic.vue"

export default {
    name: "RowDetails",
    components: {
        timeSinceRefresh,
        jsonViewer,
        iconButton,
        MISPSchemaDiagnostic,
    },
    props: {
        connection: {
            type: Object,
            required: true
        },
        serverSource: {
            type: Object,
            required: true
        },
        serverDestination: {
            type: Object,
            required: true
        }
    },
    data: function() {
        return {
            tabularView: ["", ],
            listView: ["Organisation", "RemoteOrg", "Server", "User", "connectionTest", "connectionUser"],
        }
    },
    computed: {
        getDetails() {
            // eslint-disable-next-line no-unused-vars
            return this.connection.connection
        },
    },
    methods: {
        refreshDiagnostic() {
            this.$emit("actionRefresh", "no_cache")
        },
        closeDetails() {
            this.$emit("actionClose", "no_cache")
        },
        isTabularView(name) {
            return this.tabularView.includes(name)
        },
        isListView(name) {
            return this.listView.includes(name)
        },
        fieldsFromObject(object) {
            return Object.keys(object).map(key => {
                return {
                    key: key,
                    sortable: true
                }
            })
        }
    }
}
</script>

<style scoped>

ul.nav-tabs > li.nav-item.rightmost-action > a {
    padding-bottom: 0;
    margin-top: -10px;
    margin-right: -15px;
}

ul.nav-tabs > li.nav-item.rightmost-action > a:hover {
    border: 1px solid #ffffff00;
}
ul.nav-tabs > li.nav-item.rightmost-action > a:focus {
    border: 1px solid #ffffff00;
}

.darken-on-hover > i.fas{
    color: #6c757d;
}
.darken-on-hover:hover > i.fas{
    color: #5a6268;
}

.max-heigth-700 {
    max-height: 700px;
    overflow: auto;
}
</style>