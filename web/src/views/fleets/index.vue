<template>
    <div>
        <div class="d-flex align-items-center pb-1">
            <h4>
                <img src="@/assets/fleet.svg" alt="Fleet icon" width="32" height="32" style="filter: grayscale(1);">
                Fleets
            </h4>
            <b-button
                class="ml-auto"
                size="sm"
                variant="primary"
                v-b-modal.modal-add
            >
                <iconButton text="New fleet" icon="plus"></iconButton>
            </b-button>
        </div>

        <b-list-group>
            <b-list-group-item
                v-for="(fleet, index) in getFleets"
                v-bind:key="index"
                href="#" class="p-2 flex-column align-items-start"
                :variant="getSelectedFleetId == fleet.id ? 'primary' : ''"
                @click="selectFleet(fleet)"
            >
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">{{ fleet.name }}</h5>
                    <small>{{ fleet.server_count }} {{ fleet.server_count > 1 ? "servers" : "server"}}</small>
                </div>
                <div class="d-flex">
                    <span class="d-flex flex-row justify-content-center align-items-center" style="gap: 0.5em;">
                        <span class="monitoring-icon" title="This fleet is marked to be watched" style="color: #d22f27;">
                            <span v-if="fleet.is_watched">
                                <span class="fas fa-heartbeat" style="color: #d22f27; font-size: 22px; line-height: 24px;"></span>
                            </span>
                            <span v-else>
                                <span class="fa-stack fa-1x" style="filter: grayscale(1); font-size: 10px;">
                                    <i class="fas fa-heartbeat fa-stack-2x"></i>
                                    <i class="fas fa-slash fa-stack-2x"></i>
                                </span>
                            </span>
                        </span>
                        <span class="monitoring-icon mx-1" title="This fleet is marked to be monitored" style="color: #d22f27;">
                            <img v-if="fleet.is_monitored" src="@/assets/monitored.svg" alt="Fleet monitored icon" width="24" height="24">
                            <img v-else src="@/assets/monitored-slash.svg" alt="Fleet not monitored icon" width="24" height="24" style="filter: grayscale(1);">
                        </span>
                        <span>{{ fleet.description }}</span>
                    </span>
                    <span class="ml-auto d-flex flex-row" style="gap: 0.25em;">
                        <b-button
                            class="fa fa-trash reveal-on-parent-hover"
                            size="sm"
                            variant="outline-danger"
                            v-b-modal.modal-delete-selected
                            @click.stop="selectFleetForDeletion(fleet.id)"
                        >
                        </b-button>
                        <b-button class="fa fa-edit reveal-on-parent-hover"
                            size="sm"
                            :variant="getSelectedFleetId == fleet.id ? 'outline-light' : 'outline-primary'"
                            @click.stop="openEditModal(fleet.id)">
                        </b-button>
                    </span>
                </div>
            </b-list-group-item>
        </b-list-group>

        <b-alert :show="fleetEmpty" variant="primary">
            <strong>No fleet available.</strong> Create one to get started!
        </b-alert>

        <AddModal
            :modalAction.sync="modalAction"
            :fleetForm="fleetData"
            @addition-success="handleAdd"
        ></AddModal>
        <DeleteModal
            :fleet_id="fleet_id_to_delete"
            @deletion-success="handleDelete"
        ></DeleteModal>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import iconButton from "@/components/ui/elements/iconButton.vue"
import AddModal from "@/views/fleets/AddModal.vue"
import DeleteModal from "@/views/fleets/DeleteModal.vue"
import router from "@/router"

export default {
    name: "Fleet",
    components: {
        iconButton,
        AddModal,
        DeleteModal,
    },
    data: function () {
        return {
            modalAction: "Add",
            refreshInProgress: false,
            fleetData: {},
            fleet_id_to_delete: -1,
        }
    },
    computed: {
        ...mapState({
            getSelectedFleet: state => state.fleets.selected,
            getFleets: state => state.fleets.all
        }),
        ...mapGetters({
            fleetCount: "fleets/fleetCount",
            fleetList: "fleets/fleetList",
        }),
        getSelectedFleetId () {
            return this.getSelectedFleet === null ? -1 : this.getSelectedFleet.id
        },
        fleetEmpty() {
            return this.fleetCount == 0
        },
    },
    methods: {
        selectFleet(fleet) {
            this.$store.dispatch("fleets/selectFleet", { data: fleet, redirect: true })
        },
        selectFleetForDeletion(fleet_id) {
            this.fleet_id_to_delete = fleet_id
        },
        handleAdd() {
            this.refreshFleetIndex()
        },
        handleDelete() {
            this.refreshFleetIndex()
        },
        openEditModal(fleet_id) {
            const theFleet = this.fleetList.filter((f) => f.id == fleet_id)[0]
            this.fleetData = JSON.parse(JSON.stringify(theFleet)) // deep clone
            this.modalAction = "Edit"
            this.$bvModal.show("modal-add")
        },
        refreshFleetIndex() {
            this.refreshInProgress = true
            return new Promise((resolve, reject) => {
                this.$store.dispatch("fleets/initFetch", {use_cache: false})
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        this.$bvToast.toast(error, {
                            title: "Could not fetch fleet index",
                            variant: "danger",
                        })
                        reject()
                    })
                    .finally(() => {
                        this.refreshInProgress = false
                    })
            })
        },
    },
    mounted() {
        this.refreshFleetIndex()
    }
}
</script>

<style scoped>
button.reveal-on-parent-hover {
    visibility: hidden;
}

.list-group-item:hover .reveal-on-parent-hover {
    visibility: visible;
}
.monitoring-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0;
    height: 24px;
    width: 24px;
}
.monitoring-icon svg {
    /* min-width: 24px;
    max-width: 24px; */
    flex-shrink: 0
}
</style>
