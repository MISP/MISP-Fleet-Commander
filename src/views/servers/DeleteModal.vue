<template>
    <b-modal
        id="modal-delete"
        title="Confirm Server Deletion"
        @ok.prevent="deleteServer"
    >
        <b-table-lite
            :items="[serverToDelete]"
            :fields="fields"
            stacked small responsive
        >
        </b-table-lite>

            <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="danger" @click="ok()" :disabled="postInProgress">
                <b-spinner
                    small
                    v-if="postInProgress"
                ></b-spinner>
                <span class="sr-only">Saving...</span>
                <span v-if="!postInProgress">
                    <b-icon icon="trash-fill"></b-icon> Delete
                </span>
            </b-button>
                <b-button variant="secondary" @click="cancel()">Cancel</b-button>
            </template>
    </b-modal>
</template>

<style scoped>

</style>

<script>
import axios from "axios"

export default {
    name: "DeleteModal",
    props: {
        serverToDelete: {
            type: Object,
            required: true
        },
    },
    data: function() {
        return {
            postInProgress: false,
            fields: [
                "id", "name", "url", "skip_ssl",
                {
                    key: "authkey", formatter: value => {
                        return (value === undefined || value === null) ? "" : value.slice(0, 4) + " … " + value.slice(36, 40)
                    }
                }
            ]
        }
    },
    methods: {
        deleteServer() {
            let that = this
            this.postInProgress = true
            this.$store.dispatch('servers/delete', this.serverToDelete)
                .then(() => {
                    that.$bvToast.toast("", {
                        title: "Server successfully delete",
                        variant: "success",
                    })
                    this.$emit("actionDelete", "done")
                })
                .catch(error => {
                    that.$bvToast.toast(error, {
                        title: "Could not delete Server",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.$nextTick(() => {
                        this.$bvModal.hide("modal-delete")
                    })
                    this.postInProgress = false
                })
        },
    }
}
</script>
