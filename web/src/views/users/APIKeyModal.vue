<template>
    <b-modal 
        id="modal-gen-apikey"
        title="Refresh API Key"
        size="lg"
        @hidden="resetModal"
        @ok="handleSubmission"
    >
        <div v-show="!APIKey">
            <ValidationObserver ref="observer">
                <b-form ref="modalForm" @submit.prevent="submitForm">
    
                    <b-form-group
                        label="Note"
                        label-for="input-note"
                    >
                        <ValidationProvider v-slot="validationContext" rules="required|min:0" name="Note">
                            <b-form-input
                                v-model="form.note"
                                :state="getValidationState(validationContext)"
                            ></b-form-input>
                            <small class="text-muted">What's this API key for? (Placeholder, unused for now)</small>
                            <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                        </ValidationProvider>
                    </b-form-group>
    
                </b-form>
            </ValidationObserver>
        </div>

        <div v-show="APIKey">
            <b-alert
                variant="success"
                show
            >
                <strong>The API Key has been refreshed.</strong>
                <pre class="apikey">{{ APIKey }}</pre>
            </b-alert>
        </div>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="primary" @click="ok()" :disabled="postInProgress">
                <b-spinner 
                    small
                    v-if="postInProgress"
                ></b-spinner>
                <span class="sr-only">Creating API Key...</span>
                <span v-if="!postInProgress">Create API Key</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<script>
import { ValidationProvider, ValidationObserver, extend } from "vee-validate"
import { required, min } from "vee-validate/dist/rules"

extend("required", required)
extend("min", min)

export default {
    name: "APIKeyModal",
    components: {
        ValidationProvider,
        ValidationObserver
    },
    props: {
        modalAction: {
            type: String,
            default: "Add"
        },
        userIDToGenAPIKey: {
            required: true,
        },
    },
    computed: {
    },
    data: function() {
        return {
            form: {
                note: "",
            },
            postInProgress: false,
            APIKey: false,
        }
    },
    methods: {
        getValidationState({ dirty, validated, valid = null }) {
            return dirty || validated ? valid : null
        },
        resetModal() {
            delete(this.form.id)
            this.form.note = ""
            this.$emit("update:modalAction", "GenAPIKey")
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
            this.$store.dispatch(`users/genAPIKey`, this.userIDToGenAPIKey)
                .then((apikey) => {
                    this.$nextTick(() => {
                        this.$refs.observer.reset()
                        // this.$bvModal.hide("modal-add")
                    })
                    this.$bvToast.toast(`API Key refreshed`, {
                        title: "User successfully refreshed the API key",
                        variant: "success",
                    })
                    this.$emit("addition-success", "done")
                    this.APIKey = apikey.token
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not refresh the API key for user",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.postInProgress = false
                })
        },
    },
    watch: {
        apiKeyForm: function () {
            this.form = Object.assign({}, this.apiKeyForm)
        }
    }
}
</script>

<style scoped>
.apikey {
    background-color: #eee;
    border: 1px solid #aaa;
    padding: 0.5em 1em;
    border-radius: 4px;
}
</style>