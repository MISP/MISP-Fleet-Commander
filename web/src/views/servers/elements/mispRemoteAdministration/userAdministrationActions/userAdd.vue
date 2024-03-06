<template>
    <b-modal
        id="modal-administration-user-add"
        :title="`Add User`"
        @ok="addUser"
    >
        <div>Form to add a new user</div>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="primary" @click="ok()" :disabled="requestInProgress">
                <b-spinner 
                    small
                    v-if="requestInProgress"
                ></b-spinner>
                <span class="sr-only">Saving...</span>
                <span v-if="!requestInProgress">Add User</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/userAdministration"

export default {
    name: "UserAdd",
    components: {
    },
    props: {
        user: {
            required: true,
            type: Object
        },
        server: {
            required: true,
            type: Object
        },
    },
    data: function() {
        return {
            requestInProgress: false,
            form: {},
        }
    },
    computed: {
    },
    methods: {
        addUser(evt) {
            evt.preventDefault()
            this.requestInProgress = true
            api.addUser(
                this.server.id,
                form,
                (data) => {
                    if (data.error !== undefined) {
                        this.$bvToast.toast(`Error while trying to add user`, {
                            title: data.error,
                            variant: "danger",
                            solid: true
                        })
                    } else {
                        this.$bvToast.toast(`Successfully added user`, {
                            title: data,
                            variant: "success",
                            solid: true
                        })
                        this.$nextTick(() => {
                            this.$bvModal.hide("modal-administration-user-add")
                        })
                    }
                    this.requestInProgress = false
                },
                (error) => {
                    this.$bvToast.toast(`Error while trying to add user`, {
                        title: error,
                        variant: "danger",
                        solid: true
                    })
                    this.requestInProgress = false
                }
            )
        }
    }
}
</script>

<style>

</style>