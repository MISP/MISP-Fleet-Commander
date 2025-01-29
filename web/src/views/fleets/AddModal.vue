<template>
    <b-modal 
        id="modal-add"
        :title="`${modalAction} a fleet ${form.name}`"
        size="lg"
        scrollable
        @hidden="resetModal"
        @ok="handleSubmission"
    >
        <ValidationObserver ref="observer">
            <b-form ref="modalForm" @submit.prevent="submitForm">

                <b-form-group
                    label="Fleet name"
                    label-for="input-name"
                    description="The name of the fleet acting as a group of servers"
                >
                    <ValidationProvider v-slot="validationContext" rules="required|min:3" name="Fleet name">
                        <b-form-input
                            v-model="form.name"
                            :state="getValidationState(validationContext)"
                        ></b-form-input>
                        <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                    </ValidationProvider>
                </b-form-group>

                <b-form-group
                    label="Fleet description:"
                    label-for="input-name"
                    description="Concise description of the fleet"
                >
                    <ValidationProvider v-slot="validationContext" rules="max:2048" name="Fleet description">
                        <b-form-input
                            v-model="form.description"
                            :state="getValidationState(validationContext)"
                            placeholder=""
                        ></b-form-input>
                        <b-form-invalid-feedback v-for="(error, index) in validationContext.errors" v-bind:key="index">{{ error }}</b-form-invalid-feedback>
                    </ValidationProvider>
                </b-form-group>

                <b-form-checkbox
                    id="checkbox-is-monitored"
                    v-model="form.is_monitored"
                    name="checkbox-is-monitored"
                    class="mb-1"
                >
                <div>
                    <span style="color: #d22f27;" class="mr-1">
                        <img src="@/assets/monitored.svg" alt="Fleet monitored icon" width="22" height="22">
                    </span>
                    <strong>Monitor</strong> Fleet
                </div>
                <small class="d-block text-muted">The monitoring system requires Grafana and InfluxDB to be running and reachable by the server.</small>
                </b-form-checkbox>

                <b-form-checkbox
                    id="checkbox-is-watched"
                    v-model="form.is_watched"
                    name="checkbox-is-watched"
                >
                    <span class="mr-1 fas fa-heartbeat" style="color: #d22f27;"></span>
                    <strong>Watch</strong> Fleet
                    <small class="d-block text-muted">Fleet being watched will be automatically queried and refreshed every 5min by the system.</small>
                </b-form-checkbox>
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
        fleetForm: {},
        modalAction: {
            type: String,
            default: "Add"
        },
    },
    computed: {
        isEdit() {
            return this.modalAction != "Add"
        },
        modalActionText() {
            return this.modalAction == "Add" ? "Save" : this.modalAction
        },
        formData() {
            return {
                id: this.form.id,
                name: this.form.name,
                description: this.form.description,
                is_monitored: this.form.is_monitored,
                is_watched: this.form.is_watched,
            }
        }
    },
    data: function() {
        return {
            form: this.fleetForm,
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
            this.form.is_monitored = false
            this.form.is_watched = false
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
            this.$store.dispatch(`fleets/${this.modalAction == "Add" ? "addFleet" : "editFleet"}`, this.formData)
                .then(() => {
                    this.$nextTick(() => {
                        this.$refs.observer.reset()
                        this.$bvModal.hide("modal-add")
                    })
                    this.$bvToast.toast(`${this.formData.name} ${this.isEdit ? 'updated' : 'created'}`, {
                        title: this.isEdit ? "Fleet successfully edited" : "Fleet successfully added",
                        variant: "success",
                    })
                    this.$emit("addition-success", "done")
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not save Fleet",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.postInProgress = false
                    this.$store.dispatch("fleets/getFleets")
                })
        },
    },
    watch: {
        fleetForm: function() {
            this.form = Object.assign({}, this.fleetForm)
        }
    }
}
</script>
