<template>
    <div>
        <b-card no-body
            v-show="open"
            bg-variant=""
            text-variant=""
            id="pinPanel"
            style="box-shadow: rgba(0, 0, 0, 0.07) 0px 1px 1px, rgba(0, 0, 0, 0.07) 0px 2px 2px, rgba(0, 0, 0, 0.07) 0px 4px 4px, rgba(0, 0, 0, 0.07) 0px 8px 8px, rgba(0, 0, 0, 0.07) 0px 16px 16px;"
        >

            <b-card-title class="px-2 pt-1 mb-2" style="background-color: rgba(0, 0, 0, 0.03);">
                <h5 id="sidebar-no-header-title" class="mb-0 d-flex">
                    <span>{{ totalPinnedCount }} Pinned Elements</span>
                </h5>
            </b-card-title>

            <b-tabs
                card fill small pills
                nav-wrapper-class="px-3 py-1"
                @activate-tab="updateActiveTab"
            >
                <b-tab
                    v-for="(pinTab, i) in pinTabs"
                    :key="i"
                    :active="i == 0"
                    no-body
                    style="max-height: 85vh; overflow-y: auto;"
                >
                    <template #title>
                        <span style="user-select: none;">
                            <i :class="pinTab.icon" ></i> {{ pinTab.name }}
                        </span>
                        <b-badge :variant="i == activeTabIndex ? 'light' : 'secondary'">{{ pinTab.items().length }}</b-badge>
                    </template>

                    <div class="m-2 d-flex flex-column">
                        <b-button variant="primary" @click="showPinnedContentOnNodes()" size="sm" block class="mb-1 ml-auto">
                            <i class="fa fa-eye"></i> Show pinned content on all nodes
                        </b-button>
                        <ValidationProvider v-slot="validationContext" rules="validUUID" :name="`${pinTab.name} UUID`">
                            <b-input-group size="sm">
                                <b-input-group-prepend>
                                    <b-button
                                        @click="pinEntry(pinTab.model)"
                                        variant="primary" size="sm"
                                        :disabled="!getValidationState(validationContext)"
                                    >
                                        <b-spinner small v-if="form.postInProgress"></b-spinner>
                                        <span class="sr-only">Pinning...</span>
                                        <span v-if="!form.postInProgress"><i class="fa fa-thumbtack"></i> Pin</span>
                                    </b-button>
                                </b-input-group-prepend>

                                    <b-form-input
                                        :formatter="trimmer"
                                        v-model="form.uuid"
                                        :state="getValidationState(validationContext)"
                                        type="text"
                                        :placeholder="`${pinTab.name} UUID`"
                                    ></b-form-input>
                            </b-input-group>
                        </ValidationProvider>
                    </div>

                    <div class="text-muted mx-2">
                        <small>{{ pinTab.items().length }} pinned entries</small>
                    </div>

                    <b-table-lite
                        v-show="!fetchingPinLists"
                        id="table-pinlist-events"
                        striped small
                        class="mb-0"
                        show-empty
                        :bordered="false"
                        :borderless="true"
                        :outlined="false"
                        thead-class="d-none"
                        tbody-tr-class="tiny-row"
                        :items="pinTab.items()"
                        :fields="pinFields"
                    >
                        <template #empty>
                            <div class="text-muted text-center">No entry pinned</div>
                        </template>

                        <template v-slot:cell(img)="row">
                            <Avatar :pinlist_id="row.item.id" :pinlist_model="pinTab.model" width="32" height="32"></Avatar>
                        </template>

                        <template v-slot:cell(action)="row">
                            <b-button
                                variant="link" size="xs" class="p-0"
                                title="Refresh nodes for that entry"
                                @click="refreshAllServers(row.item.id)"
                                :disabled="loadingInProgressForID == row.item.id"
                            >
                                <i class="fas fa-sync-alt"></i>
                            </b-button>
                            <b-button
                                variant="link" size="xs" class="p-0"
                                title="Remove the pinned entry"
                                @click="deleteEntry(row.item.id)"
                                :disabled="loadingInProgressForID == row.item.id"
                            >
                                <i class="fas fa-eraser"></i>
                                <i class="fa-solid fa-thumbtack-slash"></i>
                            </b-button>
                            <b-button
                                variant="link" size="xs" class="ml-1 p-0 text-danger"
                                title="Delete the pinned entry from all servers"
                                @click="deleteOnAllServers(row.item.id)"
                                :disabled="loadingInProgressForID == row.item.id"
                            >
                                <i class="fas fa-trash"></i>
                            </b-button>
                        </template>
                    </b-table-lite>
                    <div class="d-flex justify-content-center my-3" v-if="fetchingPinLists">
                        <b-spinner small></b-spinner>
                        <span class="sr-only">Fetching Pin lists...</span>
                    </div>
                </b-tab>

            </b-tabs>

        </b-card>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import { ValidationProvider, extend } from "vee-validate"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import Avatar from "@/views/strategicView/elements/avatar/Avatar.vue";

extend('validUUID', value => {
    return value.length == 36;
});

export default {
    name: "ThePinCard",
    components: {
        timeSinceRefresh,
        ValidationProvider,
        Avatar,
    },
    props: {
        open: {
            type: Boolean,
            required: true
        },
    },
    data: function() {
        return {
            activeTabIndex: 0,
            form: {
                uuid: "",
                postInProgress: false,
            },
            pinTabs: [
                { icon: 'fa fa-envelope', name: 'Events', model: 'event', items: () => this.pinnedEvents },
                { icon: 'fa fa-cube', name: 'Attributes', model: 'attribute', items: () => this.pinnedAttributes },
                { icon: 'fa fa-users', name: 'Sharing Groups', model: 'sharinggroup', items: () => this.pinnedSharingGroups },
                { icon: 'fa fa-eye', name: 'Sightings', model: 'sighting', items: () => this.pinnedSightings },
                { icon: 'fa fa-sticky-note', name: 'Analyst Data', model: 'analystdata', items: () => this.pinnedAnalystData },
            ],
            pinFields : [
                { key: "img", label: "", class: "tiny-cell-button" },
                { key: "uuid", label: "UUID", class: "tiny-cell-text" },
                { key: "action", label: "", class: "tiny-cell-button" },
            ],
            fetchingPinLists: false,
            loadingInProgressForID: null,
        }
    },
    computed: {
        ...mapGetters({
            pinnedEvents: "pinlists/pinnedEvents",
            pinnedAttributes: "pinlists/pinnedAttributes",
            pinnedSharingGroups: "pinlists/pinnedSharingGroups",
            pinnedSightings: "pinlists/pinnedSightings",
            pinnedAnalystData: "pinlists/pinnedAnalystData",
            pinnedByID: "pinlists/pinnedByID",
            entriesByServerID: "pinlists/entriesByServerID",
            entriesByPinnedID: "pinlists/entriesByPinnedID",
        }),
        totalPinnedCount: function() {
            return this.pinnedEvents.length +
                this.pinnedAttributes.length +
                this.pinnedSharingGroups.length +
                this.pinnedSightings.length +
                this.pinnedAnalystData.length 
        }
    },
    methods: {
        updateActiveTab(newTabIndex) {
            this.activeTabIndex = newTabIndex
        },
        getValidationState({ dirty, validated, valid = null }) {
            return dirty || validated ? valid : null
        },
        trimmer(value) {
            return value.trim()
        },
        close() {
            this.$emit("update:open", false)
        },
        showPinnedContentOnNodes() {
            this.$emit("showPinnedContentOnNodes", true)
        },
        pinEntry(model) {
            this.doPinning(model, this.form.uuid)
        },
        doPinning(model, uuid) {
            this.form.postInProgress = true
            const payload = {
                model: model,
                uuid: uuid,
            }
            this.$store.dispatch('pinlists/add', payload)
                .then(() => {
                    this.form[`uuid`] = ''
                })
                .catch(error => {
                    this.$bvToast.toast(error.message !== undefined ? error.message : error, {
                        title: `Could not pin ${model}`,
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.form.postInProgress = false
                })
        },
        refreshPinlists() {
            this.fetchingPinLists = true
            this.$store.dispatch("pinlists/fetchIndex")
                .catch(error => {
                    this.$bvToast.toast(error.message, {
                        title: 'Could not fetch pin lists',
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.fetchingPinLists = false
                })
            this.$store.dispatch("pinlists/getAllEntries")
                .catch(error => {
                    this.$bvToast.toast(error.message, {
                        title: 'Could not fetch pin list entries',
                        variant: "danger",
                    })
                })
        },
        deleteEntry(pinlist_id) {
            const entry = this.pinnedByID[pinlist_id]
            this.$bvModal.msgBoxConfirm(`Please confirm that you want to un-pin entry ${entry.uuid}.`, {
                title: 'Please Confirm',
                buttonSize: 'sm',
                okVariant: 'warning',
                okTitle: 'Yes',
                cancelTitle: 'No',
                footerClass: 'p-2',
                hideHeaderClose: false,
            }).then(confirm => {
                    if (!confirm) return
                    this.$store.dispatch("pinlists/delete", pinlist_id)
                        .catch(error => {
                            this.$bvToast.toast(error.message, {
                                title: 'Could not fetch delete entry',
                                variant: "danger",
                            })
                        })
                })
        },
        deleteOnAllServers(entry_id) {
            const entry = this.pinnedByID[entry_id]
            this.$bvModal.msgBoxConfirm(`Please confirm that you want to remove the data associated to the entry ${entry.uuid} from all servers.`, {
                title: 'Please Confirm',
                buttonSize: 'sm',
                okVariant: 'danger',
                okTitle: 'Yes',
                cancelTitle: 'No',
                footerClass: 'p-2',
                hideHeaderClose: false,
            }).then(confirm => {
                if (!confirm) return
                this.$store.dispatch("pinlists/deleteFromServers", entry_id)
                    .then(deletionResult => {
                        const entry = this.pinnedByID[entry_id]
                        const successes = deletionResult.filter(result => result.error === undefined)
                        const fails = deletionResult.filter(result => result.error !== undefined)
                        let message = `${entry.model} deleted from all servers`
                        let variant = 'success'
                        if (fails.length > 0) {
                            variant = successes.length > 0 ? 'success' : 'warning'
                            message = `${entry.model} deleted from ${successes.length} server(s).\n But, could not delete from ${fails.length} server(s)`
                        }
                        this.$bvToast.toast(message, {
                            title: `${entry.model} deletion from all servers`,
                            variant: variant,
                        })
                    })
                    .catch(error => {
                        this.$bvToast.toast(error.message, {
                            title: 'Error while trying to delete the entry',
                            variant: "danger",
                        })
                    })
            })
        },
        refreshAllServers(entry_id) {
            this.loadingInProgressForID = entry_id
            this.$store.dispatch("pinlists/refreshAllServers", entry_id)
                .then(() => {
                    this.$store.dispatch("pinlists/getEntriesFromPinned", entry_id)
                    .then(() => {
                        this.loadingInProgressForID = null
                    })
                })
                .catch(error => {
                    this.$bvToast.toast(error.message !== undefined ? error.message : error, {
                        title: 'Error while trying to refresh the entry on all servers',
                        variant: "danger",
                    })
                    this.loadingInProgressForID = null
                })
        }
    },
    mounted() {
        this.refreshPinlists()
    }
}
</script>

<style scoped>
    .close-button {
        right: 4px;
        top: 0;
        user-select: none;
    }
    .refresh-button {
        right: 12px;
        top: 0;
        user-select: none;
    }
    .badge {
        transition: none;
    }
</style>

<style>
    #table-pinlist-events td.tiny-cell-text {
        line-height: 1;
        vertical-align: middle;
        user-select: all;
    }
    #table-pinlist-events td.tiny-cell-button {
        padding: 0;
        vertical-align: middle
    }

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