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

                <b-form-group
                    label="Password"
                    label-for="input-name"
                >
                    <ValidationProvider v-slot="validationContext" :rules="`${actionType == 'add' ? 'required' : ''}|min:6|max:2048`" name="Password">
                        <b-form-input
                            v-model="form.password"
                            :state="getValidationState(validationContext)"
                            type="password"
                            placeholder=""
                        ></b-form-input>
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
        }
    },
    data: function() {
        return {
            form: this.userForm,
            postInProgress: false,
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
            this.$store.dispatch(`users/${this.actionType}`, this.form)
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
