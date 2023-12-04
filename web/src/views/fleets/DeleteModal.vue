<template>
    <b-modal 
        id="modal-delete-selected"
        title="Delete selected fleet"
        size="xl"
        scrollable
        @ok.prevent="handleSubmission"
    >

        <b-table-simple small :bordered="false" :borderless="true">
            <b-tbody>
                <b-tr>
                    <b-th>Fleet name</b-th>
                    <b-td class="font-mono">{{ getFleet.name }}</b-td>
                </b-tr>
                <b-tr>
                    <b-th>Description</b-th>
                    <b-td class="text-muted">{{ getFleet.description || '-- None --' }}</b-td>
                </b-tr>
                <b-tr>
                    <b-th>Server count</b-th>
                    <b-td>{{ getFleet.server_count }}</b-td>
                </b-tr>
            </b-tbody>
        </b-table-simple>

        <template v-if="getFleet.server_count > 0">
            <b-table-lite
                small 
                :fields="getServerFields"
                :items="getFleet.servers"
            >
            </b-table-lite>
        </template>
        <template v-else>
            <b-alert variant="primary" show>
                This fleet has no server
            </b-alert>
        </template>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="danger" @click="ok()" :disabled="postInProgress">
                <b-spinner 
                    small
                    v-if="postInProgress"
                ></b-spinner>
                <span class="sr-only">Deleting...</span>
                <span v-if="!postInProgress">Delete fleet</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<script>
import { mapState } from "vuex"

export default {
    name: "DeleteSelectedModal",
    props: {
        fleet_id: {
            type: Number,
            required: true
        },
    },
    data: function() {
        return {
            postInProgress: false
        }
    },
    computed: {
        ...mapState({
            getSelectedFleet: state => state.fleets.selected,
            getFleets: state => state.fleets.all
        }),
        getFleet() {
            return this.getFleets[this.fleet_id] ?? {}
        },
        getServerFields() {
            return ['id', 'name', 'url']
        },
    },
    methods: {
        handleSubmission() {
            this.postInProgress = true
            const fleet = this.getFleet
            this.$store.dispatch("fleets/deleteFleet", this.getFleet)
                .then(() => {
                    this.$nextTick(() => {
                        this.$bvModal.hide("modal-delete-selected")
                    })
                    this.$bvToast.toast(`${fleet.name} has been successfully deleted`, {
                        title: `${fleet.name} deleted`,
                        variant: "success",
                    })
                    this.$emit("deletion-success", "done")
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: `Could not delete ${fleet.name}`,
                        variant: "danger",
                    })
                })
        },
    }
}
</script>

<style scoped>

</style>
