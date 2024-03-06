<template>
    <b-modal
        id="modal-administration-user-set-password"
        :title="`Change password`"
        @ok="setPassword"
    >
        <p class="my-4">Change password for user: <pre>{{ user.User.email }}</pre></p>

        <b-row class="my-1">
            <b-col sm="3">
                <label for="password">Password</label>
            </b-col>
            <b-col sm="9">
                <b-form-input id="password" type="password" v-model="form.password" autocomplete="new-password"></b-form-input>
            </b-col>
        </b-row>
        <b-row class="my-1">
            <b-col sm="3">
                <label for="password_confirm">Confirm Password</label>
            </b-col>
            <b-col sm="9">
                <b-form-input id="password_confirm" type="password" v-model="form.password_confirm" autocomplete="new-password"></b-form-input>
            </b-col>
        </b-row>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="primary" @click="ok()" :disabled="requestInProgress || !passwordMatch">
                <b-spinner 
                    small
                    v-if="requestInProgress"
                ></b-spinner>
                <span class="sr-only">Saving...</span>
                <span v-if="!requestInProgress">{{ saveText }}</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/userAdministration"

export default {
    name: "UserSetPassword",
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
            form: {
                password: '',
                password_confirm: '',
            }
        }
    },
    computed: {
        passwordMatch: function() {
            return this.form.password == this.form.password_confirm
        },
        saveText: function() {
            return this.passwordMatch ? 'Change password' : 'Password do not match'
        }
    },
    methods: {
        setPassword(evt) {
            evt.preventDefault()
            this.requestInProgress = true
            api.setPassword(
                this.server.id,
                this.user.User.id,
                JSON.parse(JSON.stringify(this.form)),
                (data) => {
                    if (data.error !== undefined) {
                        this.$bvToast.toast(data.error, {
                            title: `Error while trying to change password`,
                            variant: "danger",
                            solid: true
                        })
                    } else {
                        this.form.password = ''
                        this.form.password_confirm = ''
                        this.$bvToast.toast(`Successfully changed password`, {
                            title: data,
                            variant: "success",
                            solid: true
                        })
                        this.$nextTick(() => {
                            this.$bvModal.hide("modal-administration-user-set-password")
                        })
                    }
                    this.requestInProgress = false
                },
                (error) => {
                    this.$bvToast.toast(`Error while trying to change password`, {
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