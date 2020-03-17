<template>
    <b-modal 
        id="modal-csv-add"
        title="Add Server from CSV"
        size="xl"
        scrollable
        @hidden="resetModal"
        @ok.prevent="handleSubmission"
    >
        <csvReader
            :selectedServers.sync="selectedServers"
            :allRequiredFieldsPicked.sync="allRequiredFieldsPicked"
        ></csvReader>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="primary" @click="ok()" :disabled="!haveSelectedServers || !allRequiredFieldsPicked">
                <b-spinner 
                    small
                    v-if="postInProgress"
                ></b-spinner>
                <span class="sr-only">Saving...</span>
                <span v-if="!postInProgress">
                    {{ !haveSelectedServers ? "No server selected" : ( !allRequiredFieldsPicked ? "Not all required column are mapped" : "Save") }}
                </span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<script>
import csvReader from "@/components/ui/elements/csvReader.vue"

export default {
    name: "CSVAddModal",
    components: {
        csvReader
    },
    data: function() {
        return {
            postInProgress: false,
            skip_ssl: false,
            file: null,
            has_header: false,
            servers: [],
            selectedServers: [],
            allRequiredFieldsPicked: false
        }
    },
    computed: {
        haveSelectedServers() {
            return this.selectedServers.length > 0
        },
        hasServers() {
            return this.servers.length > 0
        }
    },
    methods: {
        resetModal() {
        },
        handleSubmission() {
            this.postInProgress = true
            this.$store.dispatch("servers/add", this.selectedServers)
                .then(() => {
                    this.$nextTick(() => {
                        this.$bvModal.hide("modal-csv-add")
                    })
                    this.$emit("addition-success")
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not add servers from CSV",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.postInProgress = false
                })
        },
    }
}
</script>

<style scoped>

</style>