<template>
    <b-modal 
        id="modal-add"
        :title="`${modalAction} User`"
        size="lg"
        scrollable
        @hidden="resetModal"
        @ok="handleSubmission"
    >
        <ValidationObserver ref="observer">
            <b-form ref="modalForm" @submit.prevent="submitForm">

                <b-form-group
                    label="User email"
                    label-for="input-name"
                >
                    <ValidationProvider v-slot="validationContext" rules="required|email" name="Email">
                        <b-form-input
                            v-model="form.email"
                            :state="getValidationState(validationContext)"
                        ></b-form-input>
                        <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                    </ValidationProvider>
                </b-form-group>

                <b-form-group v-if="isSelf" label="Password">
                    <p class="mb-0 text-muted">
                        Change your own password from the
                        <router-link :to="{ name: 'change-password', query: { redirect: $route.fullPath } }" @click.native="$bvModal.hide('modal-add')">Change password</router-link>
                        page: it asks for your current one.
                    </p>
                </b-form-group>
                <b-form-group
                    v-else
                    label="Password"
                    label-for="input-password"
                    :description="passwordDescription"
                >
                    <ValidationProvider v-slot="validationContext" :rules="`${actionType == 'add' ? 'required|' : ''}passwordLength:${minPasswordLength}|max:2048`" name="Password">
                        <b-form-input
                            id="input-password"
                            v-model="form.password"
                            :state="getValidationState(validationContext)"
                            type="password"
                            autocomplete="new-password"
                            :placeholder="isEdit ? 'Unchanged' : ''"
                        ></b-form-input>
                        <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                    </ValidationProvider>
                </b-form-group>

                <b-form-group
                    label="Role"
                    :description="isSelf ? 'You cannot change your own role' : 'Administrators manage users and instance settings'"
                >
                    <b-form-checkbox v-model="form.is_admin" switch :disabled="isSelf">
                        Administrator
                    </b-form-checkbox>
                </b-form-group>

                <b-form-group
                    label="User Settings"
                    label-for="input-user-setting"
                >
                    <ValidationProvider v-slot="validationContext" :rules="`isJSON`" name="User Settings">
                        <b-form-textarea
                            v-model="userSettings"
                            :state="getValidationState(validationContext)"
                            type="textarea"
                            placeholder="{
    // user settings
}"
                            rows="8"
                        ></b-form-textarea>
                        <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                    </ValidationProvider>
                </b-form-group>

            </b-form>
        </ValidationObserver>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="primary" @click="ok()" :disabled="postInProgress">
                <b-spinner 
                    small
                    v-if="postInProgress"
                ></b-spinner>
                <span class="sr-only">Saving...</span>
                <span v-if="!postInProgress">Save</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<script>
import { ValidationProvider, ValidationObserver, extend } from "vee-validate"
import { required, min, max, email } from "vee-validate/dist/rules"

extend("required", required)
extend("min", min)
extend("max", max)
extend("email", email)
extend("passwordLength", {
    params: ["length"],
    validate: (value, { length }) => String(value || "").length >= Number(length),
    message: "The password must be at least {length} characters long",
})
extend('isJSON', value => {
    if (typeof value === 'object') {
        return true
    }
    try {
        JSON.parse(value)
    } catch (e) {
        return e.message
    }
    return true
})

export default {
    name: "AddModal",
    components: {
        ValidationProvider,
        ValidationObserver
    },
    props: {
        modalAction: {
            type: String,
            default: "Add"
        },
        userForm: {}
    },
    computed: {
        isEdit() {
            return this.modalAction != "Add"
        },
        modalActionText() {
            return this.modalAction == "Add" ? "Save" : this.modalAction
        },
        actionType() {
            return this.modalAction == "Add" ? "add" : "edit"
        },
        isSelf() {
            const currentUser = this.$store.getters["auth/user"]
            return this.isEdit && currentUser !== null && this.form.id === currentUser.id
        },
        passwordDescription() {
            const rule = `At least ${this.minPasswordLength} characters.`
            return this.isEdit
                ? `Leave empty to keep the current password. ${rule} A new password must be changed at the next login.`
                : `${rule} The user must choose a new password at their first login.`
        },
        userSettings: {
            get: function() {
                return this.form.user_settings !== null && typeof this.form.user_settings === 'object' ? JSON.stringify(this.form.user_settings) : this.form.user_settings
            },
            set: function(update) {
                try {
                    const parsed = JSON.parse(update);
                    this.form.user_settings = parsed
                } catch (e) {
                }
            }
        }
    },
    data: function() {
        return {
            form: this.userForm,
            postInProgress: false,
            // Same minimum as the server's
            minPasswordLength: 12,
        }
    },
    methods: {
        getValidationState({ dirty, validated, valid = null }) {
            return dirty || validated ? valid : null
        },
        resetModal() {
            delete(this.form.id)
            this.form.email = ""
            this.form.password = ""
            this.form.user_settings = ""
            this.form.is_admin = false
            this.$emit("update:modalAction", "Add")
        },
        handleSubmission(evt) {
            evt.preventDefault()
            this.$refs.observer.validate().then(success => {
                if (!success) {
                    return
                }
                this.submitForm()
            })
        },
        submitForm() {
            this.postInProgress = true
            const payload = JSON.parse(JSON.stringify(this.form))
            if (this.isSelf || !payload.password) {
                delete payload.password
            }
            this.$store.dispatch(`users/${this.actionType}`, payload)
                .then(() => {
                    this.$nextTick(() => {
                        this.$refs.observer.reset()
                        this.$bvModal.hide("modal-add")
                    })
                    this.$bvToast.toast(`${this.form.email} ${this.actionType == 'add' ? 'created': 'updated'}`, {
                        title: "User successfully saved",
                        variant: "success",
                    })
                    this.$emit("addition-success", "done")
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not save user",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.postInProgress = false
                })
        },
    },
    watch: {
        userForm: function () {
            this.form = Object.assign({}, this.userForm)
        }
    }
}
</script>
