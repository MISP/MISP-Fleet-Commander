<template>
    <b-modal
        id="modal-administration-user-add"
        :title="`Add User`"
        @ok="addUser"
        @hidden="resetForm"
    >
        <b-row class="my-1">
            <b-col sm="3">
                <label for="user-add-email">Email</label>
            </b-col>
            <b-col sm="9">
                <b-form-input id="user-add-email" type="email" v-model="form.email" :state="emailState" autocomplete="off"></b-form-input>
            </b-col>
        </b-row>
        <b-row class="my-1">
            <b-col sm="3">
                <label for="user-add-org">Organisation</label>
            </b-col>
            <b-col sm="9">
                <b-form-select id="user-add-org" v-model="form.org_id" :options="orgOptions" :state="orgState"></b-form-select>
            </b-col>
        </b-row>
        <b-row class="my-1">
            <b-col sm="3">
                <label for="user-add-role">Role</label>
            </b-col>
            <b-col sm="9">
                <b-form-select id="user-add-role" v-model="form.role_id" :options="roleOptions" :state="roleState"></b-form-select>
            </b-col>
        </b-row>
        <b-row class="my-1">
            <b-col sm="3">
                <label for="user-add-notify">Send credentials</label>
            </b-col>
            <b-col sm="9">
                <b-form-checkbox id="user-add-notify" v-model="form.notify" switch></b-form-checkbox>
            </b-col>
        </b-row>
        <b-row class="my-1">
            <b-col sm="3">
                <label for="user-add-change-pw">Change password</label>
            </b-col>
            <b-col sm="9">
                <b-form-checkbox id="user-add-change-pw" v-model="form.change_pw" switch>Require a password change at first login</b-form-checkbox>
            </b-col>
        </b-row>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="primary" @click="ok()" :disabled="requestInProgress || !formValid">
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
        users: {
            required: true,
            type: Array
        },
        server: {
            required: true,
            type: Object
        },
    },
    data: function() {
        return {
            requestInProgress: false,
            form: this.getDefaultForm(),
        }
    },
    computed: {
        orgOptions: function() {
            return this.buildOptions(this.users.map(u => u.Organisation))
        },
        roleOptions: function() {
            return this.buildOptions(this.users.map(u => u.Role))
        },
        emailState: function() {
            if (this.form.email === '') {
                return null
            }
            return /^\S+@\S+$/.test(this.form.email)
        },
        orgState: function() {
            return this.form.org_id === null ? null : true
        },
        roleState: function() {
            return this.form.role_id === null ? null : true
        },
        formValid: function() {
            return this.emailState === true && this.form.org_id !== null && this.form.role_id !== null
        },
    },
    methods: {
        getDefaultForm() {
            return {
                email: '',
                org_id: null,
                role_id: null,
                notify: true,
                change_pw: true,
            }
        },
        resetForm() {
            this.form = this.getDefaultForm()
        },
        buildOptions(items) {
            const seen = {}
            const options = [{ value: null, text: 'Select...', disabled: true }]
            items.forEach(item => {
                if (item !== undefined && item !== null && seen[item.id] === undefined) {
                    seen[item.id] = true
                    options.push({ value: item.id, text: item.name })
                }
            })
            return options
        },
        addUser(evt) {
            evt.preventDefault()
            this.requestInProgress = true
            api.addUser(
                this.server.id,
                JSON.parse(JSON.stringify(this.form)),
                (data) => {
                    if (data.error !== undefined) {
                        this.$bvToast.toast(`Error while trying to add user`, {
                            title: data.error,
                            variant: "danger",
                            solid: true
                        })
                    } else {
                        this.resetForm()
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