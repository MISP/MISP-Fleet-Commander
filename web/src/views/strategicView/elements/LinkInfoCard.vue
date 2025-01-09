<template>
    <div>
        <b-card no-body
            v-show="(hasSelection || true)"
            bg-variant=""
            text-variant=""
            id="networkLinkInfoPanel"
            style="box-shadow: rgba(0, 0, 0, 0.07) 0px 1px 1px, rgba(0, 0, 0, 0.07) 0px 2px 2px, rgba(0, 0, 0, 0.07) 0px 4px 4px, rgba(0, 0, 0, 0.07) 0px 8px 8px, rgba(0, 0, 0, 0.07) 0px 16px 16px;"
        >
            <div class="border-bottom">
                <div class="d-flex flex-column align-items-center mx-2 my-3">
                    <h6 class="mb-0">{{ getSourceServer.name }}</h6>
                    <a
                        :href="getSourceServer.url"
                        target="_blank"
                        class="text-muted font-weight-light text-wrap"
                        style="font-size: 0.8em;"
                    >
                        {{ getSourceServer.url }}
                        <sup class="fa fa-external-link-alt text-muted"></sup>
                    </a>
                    <i class="fa fa-arrow-down my-1" style="font-size: 1.5em;"
                        :style="{color: !connectionHasRules ? '#2ca1db' : '#f5854d', filter: !connectionHasRules ? 'drop-shadow(0px 1px 1px rgba(0, 0, 0, .7))' : 'drop-shadow(0px 1px 1px #5b4a4299)'}"
                    ></i>
                    <h6 class="mb-0">{{ getTargetServer.name }}</h6>
                    <a
                        :href="getTargetServer.url"
                        target="_blank"
                        class="text-muted font-weight-light text-wrap"
                        style="font-size: 0.8em;"
                    >
                        {{ getTargetServer.url }}
                        <sup class="fa fa-external-link-alt text-muted"></sup>
                    </a>
                </div>
            </div>
            <b-tabs
                card fill pills
                nav-wrapper-class="px-3 py-1"
            >
                <b-tab title="Connection Info" active no-body>
                    <b-table-simple striped small class="mb-0">
                        <b-tbody>
                            <b-tr>
                                <b-th>Status</b-th>
                                <b-td>
                                    <connectionStatus
                                        :connection="getConnection"
                                    ></connectionStatus>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>Local Version</b-th>
                                <b-td>
                                    <ConnectionLocalVersion
                                        :connection="getConnection"
                                    ></ConnectionLocalVersion>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>Remote Version</b-th>
                                <b-td>
                                    <ConnectionRemoteVersion
                                        :connection="getConnection"
                                    ></ConnectionRemoteVersion>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>Compatibility</b-th>
                                <b-td>
                                    <ConnectionCompatibility
                                        :connection="getConnection"
                                    ></ConnectionCompatibility>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>POST Test</b-th>
                                <b-td>
                                    <ConnectionPostTest
                                        :connection="getConnection"
                                    ></ConnectionPostTest>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>User</b-th>
                                <b-td>
                                    <ConnectionUser
                                        :connection="getConnection"
                                    ></ConnectionUser>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>User Role</b-th>
                                <b-td>
                                    <ConnectionUserRole
                                        :connection="getConnection"
                                    ></ConnectionUserRole>
                                </b-td>
                            </b-tr>
                            <b-tr>
                                <b-th>User Sync Flag</b-th>
                                <b-td>
                                    <ConnectionSyncStatus
                                        :connection="getConnection"
                                    ></ConnectionSyncStatus>
                                </b-td>
                            </b-tr>
                        </b-tbody>
                    </b-table-simple>

                    <div class="p-2">
                        <b-button
                            variant="primary" size="sm" block
                            :href="`${getSourceServer.url}/servers/edit/${getTargetServerIDForSource}`"
                            target="_blank"
                        >
                            Edit Connection in MISP
                            <sup class="fa fa-external-link-alt"></sup>
                        </b-button>
                    </div>

                </b-tab>

                <b-tab title="Edit Connection" no-body class="p-2">
                    <b-overlay :show="saveInProgress" rounded="sm">
                        <div class="text-center"><strong style="font-size: 1.25em">General Settings</strong></div>
                        <div class="d-flex flex-column pt-2" style="gap: 0.5em;">
                            <b-input-group size="sm" prepend="URL">
                                <b-form-input :value="connectionForm.url" disabled></b-form-input>
                            </b-input-group>
                            <b-input-group size="sm" prepend="Instance Name">
                                <b-form-input v-model="connectionForm.name"></b-form-input>
                            </b-input-group>
                            <b-input-group size="sm" prepend="Organisation Name">
                                <b-form-input v-model="connectionForm.remote_org_id"></b-form-input>
                            </b-input-group>
                        </div>

                        <div class="text-center mt-2"><strong style="font-size: 1.25em">Synchronisation Methods</strong></div>
                        <div class="d-flex mt-2" style="gap: 0.5em;">
                            <div>
                                <b-form-checkbox
                                    v-model="connectionForm.push"
                                >Push</b-form-checkbox>
                                <b-form-checkbox
                                    v-model="connectionForm.push_sightings"
                                >Push Sightings</b-form-checkbox>
                                <b-form-checkbox
                                    v-model="connectionForm.push_galaxy_clusters"
                                >Push Galaxy Clusters</b-form-checkbox>
                                <b-form-checkbox
                                    v-model="connectionForm.push_analyst_data"
                                >Push Analyst Data</b-form-checkbox>
                            </div>
                            <div>
                                <b-form-checkbox
                                    v-model="connectionForm.pull"
                                >Pull</b-form-checkbox>
                                <b-form-checkbox
                                    v-model="connectionForm.pull_galaxy_clusters"
                                >Pull Galaxy Clusters</b-form-checkbox>
                                <b-form-checkbox
                                    v-model="connectionForm.pull_analyst_data"
                                >Pull Analyst Data</b-form-checkbox>
                                <b-form-checkbox
                                    v-model="connectionForm.caching_enabled"
                                >Caching Enabled</b-form-checkbox>
                            </div>
                        </div>

                        <div class="text-center mt-2"><strong style="font-size: 1.25em">Misc Settings</strong></div>
                        <div class="d-flex flex-column mt-2" style="">
                            <b-form-checkbox
                                v-model="connectionForm.unpublish_event"
                            >Unpublish event when pushing to remote server</b-form-checkbox>
                            <b-form-checkbox
                                v-model="connectionForm.publish_without_email"
                            >Publish Without Email</b-form-checkbox>
                            <b-form-checkbox
                                v-model="connectionForm.self_signed"
                            >Allow self signed certificates (unsecure)</b-form-checkbox>
                            <b-form-checkbox
                                v-model="connectionForm.skip_proxy"
                            >Skip proxy (if applicable)</b-form-checkbox>
                            <b-form-checkbox
                                v-model="connectionForm.remove_missing_tags"
                            >Remove Missing Attribute Tags (not recommended)</b-form-checkbox>
                        </div>
                    </b-overlay>

                    <b-button
                        variant="primary" size="sm" block
                        class="mt-2"
                        :disabled="!connectionFormHasModification || saveInProgress"
                        :title="connectionFormHasModification ? `Save changes on ${getSourceServer.name}` : 'No modification'"
                        @click="submitConnectionForm"
                    >
                        <b-spinner small v-if="saveInProgress"></b-spinner>
                        <span v-else>
                            <i class="fa fa-save"></i>
                            Save changes
                        </span>
                    </b-button>
                </b-tab>

                <b-tab title="Rules" no-body>
                    <template #title>
                        Rules <b-badge :variant="connectionHasRules ? 'primary' : 'secondary'">{{ connectionRuleNumber }}</b-badge>
                    </template>
                    
                    <ConnectionRules
                        :connection="getConnection"
                    ></ConnectionRules>
                </b-tab>
            </b-tabs>

        </b-card>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import connectionStatus from "@/views/servers/elements/connectionStates/connectionStatus.vue"
import ConnectionLocalVersion from "@/views/servers/elements/connectionStates/connectionLocalVersion.vue";
import ConnectionRemoteVersion from "@/views/servers/elements/connectionStates/connectionRemoteVersion.vue";
import ConnectionSyncStatus from "@/views/servers/elements/connectionStates/connectionSyncStatus.vue";
import ConnectionUser from "@/views/servers/elements/connectionStates/connectionUser.vue";
import ConnectionUserRole from "@/views/servers/elements/connectionStates/connectionUserRole.vue";
import ConnectionCompatibility from "@/views/servers/elements/connectionStates/connectionCompatibility.vue";
import ConnectionPostTest from "@/views/servers/elements/connectionStates/connectionPostTest.vue";
import ConnectionRules from "@/views/strategicView/elements/ConnectionRules.vue";

export default {
    name: "TheLinkInfoCard",
    components: {
        timeSinceRefresh,
        connectionStatus,
        ConnectionLocalVersion,
        ConnectionRemoteVersion,
        ConnectionSyncStatus,
        ConnectionUser,
        ConnectionUserRole,
        ConnectionCompatibility,
        ConnectionPostTest,
        ConnectionRules,
    },
    props: {
        link_id: {
            type: String,
            required: true
        },
        link: {
            type: Object,
        },
    },
    data: function() {
        return {
            fields: [
                { key: "property", thStyle: { display: "none" } },
                { key: "value", thStyle: { display: "none" } }
            ],
            connectionForm: {},
            saveInProgress: false
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
            connections: state => state.connections.all,
            server_status: state => state.servers.server_status,
            server_usage: state => state.servers.server_usage,
            server_user: state => state.servers.server_user,
        }),
        getConnection: function() {
            return this.connections.filter((connection) => {
                return connection.vid == this.link_id
            })[0] || {}
        },
        getSourceServer: function() {
            return this.getConnection.source || null
        },
        getTargetServer: function() {
            return this.link.target || null
        },
        getTargetServerIDForSource: function() {
            return this.getTargetServerForSource.id || null
        },
        getTargetServerForSource: function() {
            // return this.link.destination.Server || null
            return this.getConnection.destination.Server || null
        },
        connectionHasRules: function() {
            return this.connectionRuleNumber > 0
        },
        connectionRuleNumber: function() {
            return !this.getConnection.filtering_rules ? 0 : this.getConnection.filtering_rules.pull_rule_number + this.getConnection.filtering_rules.push_rule_number
        },
        isOnline: function() {
            return !this.getServerStatus.error
        },
        hasSelection() {
            return false
        },
        serverInfoTable() {
            return []
        },
        connectionFormHasModification() {
            return JSON.stringify(this.connectionForm) != JSON.stringify(this.getTargetServerForSource)
        }
    },
    methods: {
        submitConnectionForm() {
            const payload = {
                server_id: this.getSourceServer.id,
                remote_server_id: this.getTargetServerIDForSource,
                payload: this.connectionForm
            }
            this.saveInProgress = true
            this.$store.dispatch('connections/editRemoteConnection', payload)
                .then(() => {
                })
                .catch(error => {
                    this.$bvToast.toast(error.message !== undefined ? error.message : error, {
                        title: `Could not save changes`,
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.saveInProgress = false
                })
        }
    },
    watch: {
        getTargetServerForSource: function(newData) {
            this.connectionForm = JSON.parse(JSON.stringify(newData))
        },
    },
    mounted() {
        this.connectionForm = JSON.parse(JSON.stringify(this.getTargetServerForSource))
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
