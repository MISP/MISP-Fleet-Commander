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
            :fields="getServerFields"
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
            return JSON.parse(JSON.stringify(this.servers))
        },
        getServerFields() {
            return ['id', 'name', 'url', 'skip_ssl', 'comment']
        },
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
