<template>
    <b-modal 
        id="modal-delete-selected"
        title="Delete selected servers"
        size="xl"
        scrollable
        @ok.prevent="handleSubmission"
    >
        <b-table-lite
            small 
            :items="getServers"
        >
        </b-table-lite>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="danger" @click="ok()" :disabled="postInProgress">
                <b-spinner 
                    small
                    v-if="postInProgress"
                ></b-spinner>
                <span class="sr-only">Saving...</span>
                <span v-if="!postInProgress">Delete</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<script>
export default {
    name: "DeleteSelectedModal",
    props: {
        servers: {
            type: Array,
            required: true
        }
    },
    data: function() {
        return {
            postInProgress: false
        }
    },
    computed: {
        getServers() {
            let simplifiedServers = []
            this.servers.forEach(server => {
                simplifiedServers.push({
                    id: server.id,
                    name: server.name,
                    comment: server.comment,
                    url: server.url,
                    auth_method: server.auth_method,
                    authkey: server.authkey
                })
            })
            return simplifiedServers
        }
    },
    methods: {
        handleSubmission() {
            this.postInProgress = true
            this.$store.dispatch("servers/delete", this.getServers)
                .then(() => {
                    this.$nextTick(() => {
                        this.$bvModal.hide("modal-delete-selected")
                    })
                    this.$emit("deletion-success")
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not delete selected servers",
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