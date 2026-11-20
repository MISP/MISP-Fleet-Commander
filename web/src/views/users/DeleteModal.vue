<template>
    <b-modal
        id="modal-delete"
        title="Confirm User Deletion"
        @ok.prevent="deleteUser"
    >
        <b-table-lite
            :items="[userToDelete]"
            :fields="fields"
            stacked small responsive
        >
        </b-table-lite>
        <p class="delete-consequence">
            <i class="fas fa-triangle-exclamation" aria-hidden="true"></i>
            Their fleets and servers are deleted with them, with everything kept about those servers (usage history,
            saved query answers), and so are their saved queries, baselines, pin lists, acknowledgements and settings.
            Their jobs stay on the Jobs page, shown as by a deleted user.
        </p>

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
.delete-consequence {
    display: flex;
    gap: 0.5rem;
    align-items: baseline;
    margin: 0.75rem 0 0;
    font-size: 0.875rem;
    color: var(--health-critical-ink);
}
</style>

<script>

export default {
    name: "DeleteModal",
    props: {
        userToDelete: {
            type: Object,
            required: true
        },
    },
    data: function() {
        return {
            postInProgress: false,
            fields: [
                'email', 'created', 'updated'
            ]
        }
    },
    methods: {
        deleteUser() {
            let that = this
            this.postInProgress = true
            this.$store.dispatch('users/delete', this.userToDelete.id)
                .then(() => {
                    that.$bvToast.toast(`Delete user ${this.userToDelete.email}`, {
                        title: "User successfully deleted",
                        variant: "success",
                    })
                    this.$emit("deletion-success", "done")
                })
                .catch(error => {
                    that.$bvToast.toast(error, {
                        title: "Could not delete user",
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
