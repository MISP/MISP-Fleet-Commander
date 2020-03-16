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
                    label="Server Description:"
                    label-for="input-name"
                    description="Short server description"
                >
                    <ValidationProvider v-slot="validationContext" name="Server Description">
                        <b-form-input
                            v-model="form.description"
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
                            <template v-slot:append>
                                <b-input-group-text>
                                    <ValidationProvider v-slot="">
                                        <b-form-checkbox v-model="form.skip_ssl" switch>
                                            <small>Skip SSL validation</small>
                                        </b-form-checkbox>
                                    </ValidationProvider>
                                </b-input-group-text>
                            </template>
                         </b-input-group>

                        <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                    </ValidationProvider>
                </b-form-group>

                <b-form-group
                    label="User Authorization Key:"
                    label-for="input-authkey"
                    description="The authorisation information of the user"
                >
                    <template v-slot:label>
                        <div class="d-flex">
                            Authorization:
                            <b-form-radio-group
                                class="d-inline-block ml-auto"
                                v-model="authMethodSelected"
                                :options="authMethodOptions"
                                name="radio-inline"
                            ></b-form-radio-group>
                        </div>
                    </template>

                    <div v-if="authMethodSelected == 'api'">
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
                    </div>
                    <div v-else>
                        <ValidationProvider v-slot="validationContext" rules="required|email" name="User Email">
                            <b-input-group class="mb-2">
                                <template v-slot:prepend>
                                   <b-input-group-text ><i class="fas fa-at"></i></b-input-group-text>
                                </template>
                                <b-form-input
                                    v-model="basicEmail"
                                    :state="getValidationState(validationContext)"
                                    placeholder="admin@admin.test"
                                    autocomplete="off"
                                    type="search"
                                ></b-form-input>
                                <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                            </b-input-group>
                        </ValidationProvider>
                        <ValidationProvider v-slot="validationContext" rules="required" name="User Password">
                            <b-input-group>
                                <template v-slot:prepend>
                                    <b-input-group-text ><i class="fas fa-key"></i></b-input-group-text>
                                </template>
                                <b-form-input
                                    v-model="basicPassword"
                                    type="password"
                                    :state="getValidationState(validationContext)"
                                    placeholder="Password1234"
                                    autocomplete="off"
                                ></b-form-input>
                                <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                            </b-input-group>
                        </ValidationProvider>
                    </div>
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
import axios from "axios"

extend("required", required)
extend("min", min)
extend("length", length)
extend("email", email)
extend("url", {
    validate: value => {
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
        modalActionText() {
            return this.modalAction == "Add" ? "Save" : this.modalAction
        },
        basicEmail: {
            get: function() {
                return this.basic.email
            },
            set: function(newValue) {
                this.basic.email = newValue
                this.form.basicauth = `${this.basic.email}:${this.basic.password}`
            }
        },
        basicPassword: {
            get: function() {
                return this.basic.password
            },
            set: function(newValue) {
                this.basic.password = newValue
                this.form.basicauth = `${this.basic.email}:${this.basic.password}`
            }
        },
        authMethodSelected: {
            get: function() {
                if (this.form.auth_method === undefined) {
                    return this.localAuthMethodSelected
                } else if (this.form.auth_method.length == 1 && this.form.auth_method[0] == "Basic Auth") {
                    return "basic"
                } else {
                    return this.localAuthMethodSelected
                }
            },
            set: function(newValue) {
                this.localAuthMethodSelected = newValue
            }
        }
    },
    data: function() {
        return {
            basic: {
                email: "",
                password: ""
            },
            form: this.serverForm,
            postInProgress: false,
            localAuthMethodSelected: "api",
            authMethodOptions: [
                { text: "API authorisation", value: "api" },
                { text: "Basic authorisation (email:password)", value: "basic" }
            ]
        }
    },
    methods: {
        getValidationState({ dirty, validated, valid = null }) {
            return dirty || validated ? valid : null
        },
        resetModal() {
            delete(this.form.id)
            this.form.name = ""
            this.form.description = ""
            this.form.url = ""
            this.form.skip_ssl = false
            this.form.authkey = ""
            this.form.basicauth = ""
            this.basic.email = ""
            this.basic.password = ""
            this.form.recursive_add = true
            this.authMethodSelected = "api"
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
            let url = "http://127.0.0.1:5000/servers/"
            if (this.modalAction == "Add") {
                url += "add"
            } else {
                url += "edit"
            }
            this.postInProgress = true
            let that = this
            axios.post(url, this.form)
                .then((response) => {
                    this.$nextTick(() => {
                        this.$refs.observer.reset()
                    })
                    this.$nextTick(() => {
                        this.$bvModal.hide("modal-add")
                    })
                    const toastText = response.data.name + " [" + response.data.url + "]"
                    that.$bvToast.toast(toastText, {
                        title: "Server successfully added",
                        variant: "success",
                    })
                })
                .catch(error => {
                    that.$bvToast.toast(error, {
                        title: "Could not save Server",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.postInProgress = false
                    this.$emit("addition-success", "done")
                })
        },
    },
    watch: {
        serverForm: function() {
            this.form = this.serverForm
        }
    }
}
</script>