<template>
    <b-modal
        id="modal-administration-user-reset-password"
        :title="`Reset password for User`"
        @ok="resetPassword"
    >
        <p class="my-4">Confirm resetting password for user: <pre>{{ user.User.email }}</pre></p>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="primary" @click="ok()" :disabled="requestInProgress">
                <b-spinner 
                    small
                    v-if="requestInProgress"
                ></b-spinner>
                <span class="sr-only">Saving...</span>
                <span v-if="!requestInProgress">Reset password</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/userAdministration"

export default {
    name: "UserResetPassword",
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
        }
    },
    computed: {
    },
    methods: {
        resetPassword(evt) {
            evt.preventDefault()
            this.requestInProgress = true
            api.resetPassword(
                this.server.id,
                this.user.User.id,
                (data) => {
                    if (data.error !== undefined) {
                        this.$bvToast.toast(`Error while trying to reset password for user`, {
                            title: data.error,
                            variant: "danger",
                            solid: true
                        })
                    } else {
                        this.$bvToast.toast(`Successfully reset password of user`, {
                            title: data,
                            variant: "success",
                            solid: true
                        })
                        this.$nextTick(() => {
                            this.$bvModal.hide("modal-administration-user-reset-password")
                        })
                    }
                    this.requestInProgress = false
                },
                (error) => {
                    this.$bvToast.toast(`Error while trying to reset password of user`, {
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