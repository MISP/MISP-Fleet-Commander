<template>
    <b-modal
        id="modal-administration-user-disable"
        :title="`${disableText} User`"
        @ok="disableUser"
    >
        <p class="my-4">Confirm {{ disablingText }} user: <pre>{{ user.User.email }}</pre></p>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="primary" @click="ok()" :disabled="requestInProgress">
                <b-spinner 
                    small
                    v-if="requestInProgress"
                ></b-spinner>
                <span class="sr-only">Saving...</span>
                <span v-if="!requestInProgress">{{ disableText}} User</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/userAdministration"

export default {
    name: "UserDisable",
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
        isDisabled: {
            required: true,
            type: Boolean,
        }
    },
    data: function() {
        return {
            requestInProgress: false,
        }
    },
    computed: {
        disableText() {
            return this.isDisabled ? 'Enable' : 'Disable'
        },
        disabledText() {
            return this.isDisabled ? 'Enabled' : 'Disabled'
        },
        disablingText() {
            return this.isDisabled ? 'Enabling' : 'Disabling'
        },
        disableFun() {
            return this.isDisabled ? api.enable : api.disable
        }
    },
    methods: {
        disableUser(evt) {
            evt.preventDefault()
            this.requestInProgress = true
            this.disableFun(
                this.server.id,
                this.user.User.id,
                (data) => {
                    if (data.error !== undefined) {
                        this.$bvToast.toast(`Error while trying to ${this.disableText} user`, {
                            title: data.error,
                            variant: "danger",
                            solid: true
                        })
                    } else {
                        this.$bvToast.toast(`Successfully ${this.disabledText} user`, {
                            title: data,
                            variant: "success",
                            solid: true
                        })
                        this.$nextTick(() => {
                            this.$bvModal.hide("modal-administration-user-disable")
                        })
                    }
                    this.requestInProgress = false
                },
                (error) => {
                    this.$bvToast.toast(`Error while trying to ${this.disableText} user`, {
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