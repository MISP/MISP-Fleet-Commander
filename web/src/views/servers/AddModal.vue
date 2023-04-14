<template>
    <b-modal 
        id="modal-add"
        :title="`${modalAction} Server`"
        size="lg"
        scrollable
        @hidden="resetModal"
        @ok="handleSubmission"
    >
        <ValidationObserver ref="observer">
            <b-form ref="modalForm" @submit.prevent="submitForm">

                <b-form-group
                    label="Server Name:"
                    label-for="input-name"
                    description="Local name of the server"
                >
                    <ValidationProvider v-slot="validationContext" rules="required|min:4" name="Server Name">
                        <b-form-input
                            v-model="form.name"
                            :state="getValidationState(validationContext)"
                        ></b-form-input>
                        <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                    </ValidationProvider>
                </b-form-group>

                <b-form-group
                    label="Server Comment:"
                    label-for="input-name"
                    description="Short server comment"
                >
                    <ValidationProvider v-slot="validationContext" name="Server Comment">
                        <b-form-input
                            v-model="form.comment"
                            :state="getValidationState(validationContext)"
                            placeholder=""
                        ></b-form-input>
                        <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                    </ValidationProvider>
                </b-form-group>
                <b-form-group
                    label="Server URL:"
                    label-for="input-url"
                    description="The URL to access the server"
                >
                    <ValidationProvider v-slot="validationContext" rules="required|url" name="Server URL">
                        <b-input-group>
                            <b-form-input
                                v-model="form.url"
                                :state="getValidationState(validationContext)"
                                placeholder="https://misp.test"
                                type="url"
                            ></b-form-input>
                                <b-input-group-append>
                                    <b-input-group-text>
                                        <ValidationProvider v-slot="validationContext" name="Skip SSL">
                                            <b-form-checkbox v-model="form.skip_ssl" switch>
                                                <small>Skip SSL validation</small>
                                            </b-form-checkbox>
                                        </ValidationProvider>
                                    </b-input-group-text>
                                </b-input-group-append>
                         </b-input-group>

                        <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                    </ValidationProvider>
                </b-form-group>

                <b-form-group
                    label="Authorization Key:"
                    label-for="input-authkey"
                    description="The authorisation information of the user"
                >
                    <ValidationProvider v-slot="validationContext" rules="required|length:40" name="User AUTHKey">
                        <b-form-input
                            v-model="form.authkey"
                            :state="getValidationState(validationContext)"
                            placeholder="3vl1KgDgQ1m0W3rwKMgB5z6MqfYkUZobGwIj3Urw"
                            autocomplete="off"
                            type="search"
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
                <span v-if="!postInProgress">{{ modalActionText }}</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<style scoped>

</style>

<script>
import { ValidationProvider, ValidationObserver, extend } from "vee-validate"
import { required, min, length, email } from "vee-validate/dist/rules"

extend("required", required)
extend("min", min)
extend("length", length)
extend("email", email)
extend("url", {
   validate: value => {
       // eslint-disable-next-line no-useless-escape
       const pattern2 = /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)/
       return pattern2.test(value)
   },
   message: "This field must be a valid URL"
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
        serverForm: {}
    },
    computed: {
        isEdit() {
            return this.modalAction != "Add"
        },
        modalActionText() {
            return this.modalAction == "Add" ? "Save" : this.modalAction
        },
    },
    data: function() {
        return {
            skip_ssl: false,
            form: this.serverForm,
            postInProgress: false,
        }
    },
    methods: {
        getValidationState({ dirty, validated, valid = null }) {
            return dirty || validated ? valid : null
        },
        resetModal() {
            delete(this.form.id)
            this.form.name = ""
            this.form.comment = ""
            this.form.url = ""
            this.form.skip_ssl = false
            this.form.authkey = ""
            this.form.recursive_add = true
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
            this.$store.dispatch(`servers/${this.modalAction == "Add" ? "add" : "edit"}`, this.form)
                .then((response) => {
                    this.$nextTick(() => {
                        this.$refs.observer.reset()
                        this.$bvModal.hide("modal-add")
                    })
                    const toastText = response.data.name + " [" + response.data.url + "]"
                    const messageText = this.isEdit ? "Server successfully edited" : "Server successfully added"
                    this.$bvToast.toast(toastText, {
                        title: messageText,
                        variant: "success",
                    })
                    this.$emit("addition-success", "done")
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not save Server",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.postInProgress = false
                })
        },
    },
    watch: {
        serverForm: function() {
            this.form = Object.assign({}, this.serverForm)
        }
    }
}
</script>
