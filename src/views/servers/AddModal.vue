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
                            v-model="serverForm.name"
                            :state="getValidationState(validationContext)"
                            placeholder="Production MISP"
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
                        <div class="input-group">
                            <b-form-input
                                v-model="serverForm.url"
                                :state="getValidationState(validationContext)"
                                placeholder="https://misp.test"
                            ></b-form-input>
                            <div class="input-group-append">
                                <div class="input-group-text">
                                    <ValidationProvider v-slot="">
                                        <b-form-checkbox v-model="serverForm.skip_ssl" switch>
                                            <small>Skip SSL validation</small>
                                        </b-form-checkbox>
                                    </ValidationProvider>
                                </div>
                            </div>
                        </div>

                        <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                    </ValidationProvider>
                </b-form-group>

                <b-form-group
                    label="User Authorization Key:"
                    label-for="input-authkey"
                    description="The AUTHKey or API Key of the user"
                >
                    <ValidationProvider v-slot="validationContext" rules="required|length:40" name="User AUTHKey">
                        <b-form-input
                            v-model="serverForm.authkey"
                            :state="getValidationState(validationContext)"
                            placeholder="3vl1KgDgQ1m0W3rwKMgB5z6MqfYkUZobGwIj3Urw"
                        ></b-form-input>
                        <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                    </ValidationProvider>
                </b-form-group>

                <b-form-group
                    description="By checking this box, it will try to add other MISP Servers connected to this one using known remote Servers"
                >
                    <b-form-checkbox v-model="serverForm.recursive_add">Recursively Add Servers</b-form-checkbox>
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
                <span v-if="!postInProgress">{{ modalAction == "Add" ? "Save" : modalAction}}</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<style scoped>

</style>

<script>
import { ValidationProvider, ValidationObserver, extend } from "vee-validate"
import { required, min, length } from "vee-validate/dist/rules"
import axios from "axios"

extend("required", required)
extend("min", min)
extend("length", length)
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
        ValidationObserver,
    },
    props: {
        modalAction: {
            type: String,
            default: "Add"
        },
        serverForm: {
            type: Object,
            default: () => {
                return {
                    name: "",
                    url: "",
                    skip_ssl: false,
                    authkey: "",
                    recursive_add: true
                }
            }
        }
    },
    data: function() {
        return {
            postInProgress: false,
        }
    },
    methods: {
        getValidationState({ dirty, validated, valid = null }) {
            return dirty || validated ? valid : null
        },
        resetModal() {
            delete(this.serverForm.id)
            this.serverForm.name = ""
            this.serverForm.url = ""
            this.serverForm.skip_ssl = false
            this.serverForm.authkey = ""
            this.serverForm.recursive_add = true
            this.modalAddAction = "Add"
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
            axios.post(url, this.serverForm)
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
                    this.$emit("actionAdd", "done")
                })
        },
    }
}
</script>