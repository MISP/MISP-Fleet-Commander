<template>
    <b-modal 
        id="modal-add"
        title="Add Server Group"
        size="lg"
        scrollable
        @hidden="resetModal"
        @ok="handleSubmission"
    >
        <ValidationObserver ref="observer">
            <b-form ref="modalForm" @submit.prevent="submitForm">

                <b-form-group
                    label="Server Group Name:"
                    label-for="input-name"
                    description="The name of the server group"
                >
                    <ValidationProvider v-slot="validationContext" rules="required|min:3" name="Server Group Name">
                        <b-form-input
                            v-model="form.name"
                            :state="getValidationState(validationContext)"
                        ></b-form-input>
                        <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                    </ValidationProvider>
                </b-form-group>

                <b-form-group
                    label="Server Group Description:"
                    label-for="input-name"
                    description="Concise description of the server group"
                >
                    <ValidationProvider v-slot="validationContext" rules="max:2048" name="Server Group Description">
                        <b-form-input
                            v-model="form.description"
                            :state="getValidationState(validationContext)"
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
                <span v-if="!postInProgress">Add</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<script>
import { ValidationProvider, ValidationObserver, extend } from "vee-validate"
import { required, min, max } from "vee-validate/dist/rules"
// import axios from "axios"

extend("required", required)
extend("min", min)
extend("max", max)

export default {
    name: "AddModal",
    components: {
        ValidationProvider,
        ValidationObserver
    },
    props: {
        groupForm: {}
    },
    computed: {
        formData() {
            return {
                name: this.form.name,
                description: this.form.description,
            }
        }
    },
    data: function() {
        return {
            form: this.groupForm,
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
            this.form.description = ""
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
            this.$store.dispatch("serverGroups/addServerGroup", this.formData)
                .then(() => {
                    this.$nextTick(() => {
                        this.$refs.observer.reset()
                        this.$bvModal.hide("modal-add")
                    })
                    this.$bvToast.toast(`${this.formData.name} created`, {
                        title: "Server group successfully added",
                        variant: "success",
                    })
                    this.$emit("addition-success", "done")
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not save Server group",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.postInProgress = false
                    this.$store.dispatch("serverGroups/getServerGroups")
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