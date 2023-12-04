<template>
    <div>
        <div class="d-flex align-items-center pb-1">
            <h4><i class="fas fa-layer-group mr-2"></i>Fleets</h4>
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
                :active="getSelectedFleetId == fleet.id"
                @click="selectFleet(fleet)"
            >
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">{{ fleet.name }}</h5>
                    <small>{{ fleet.server_count }} {{ fleet.server_count > 1 ? "servers" : "server"}}</small>
                </div>
                <div class="d-flex">
                    <span>{{ fleet.description }}</span>
                    <span class="ml-auto">
                        <b-button
                            class="ml-auto fa fa-trash reveal-on-parent-hover"
                            size="sm"
                            variant="outline-danger"
                            v-b-modal.modal-delete-selected
                            @click.stop="selectFleetForDeletion(fleet.id)"
                        >
                        </b-button>
                    </span>
                </div>
            </b-list-group-item>
        </b-list-group>

        <b-alert :show="fleetEmpty" variant="primary">
            <strong>No fleet available.</strong> Create one to get started!
        </b-alert>

        <AddModal
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
            fleetCount: "fleets/fleetCount"
        }),
        getSelectedFleetId () {
            return this.getSelectedFleet === null ? -1 : this.getSelectedFleet.id
        },
        fleetEmpty() {
            return this.fleetCount == 0
        }
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
</style>
