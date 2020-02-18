<template>
<Layout name="LayoutDefault">
    <div>
        <h3>
            <iconForScope scope="servers"></iconForScope>
            MISP Servers
        </h3>

        <div class="mb-3">
            <b-button
                size="sm"
                variant="success"
                v-b-modal.modal-add
            >
                <b-icon icon="plus"></b-icon>Add Server
            </b-button>
        </div>
        
        <div class="d-flex flex-row-reverse align-items-center">
            <b-button variant="link" size="sm" @click="$refs.serverTable.refresh()">
                <b-icon icon="arrow-clockwise" :class="{'fa-spin': refreshInProgress}" title="Refresh Servers"></b-icon>
            </b-button>
            <b-input-group size="sm" class="w-25">
                <b-form-input
                    v-model="table.filter"
                    type="search"
                    id="filterInput"
                    placeholder="Type to Search"
                    class="border-bottom-0 rounded-top align-self-end"
                    style="border-radius: 0"
                ></b-form-input>
            </b-input-group>
        </div>
        <b-table 
            striped hover show-empty small
            ref="serverTable"
            :per-page="table.perPage"
            :current-page="table.currentPage"
            :busy.sync="table.isBusy"
            :items="getIndex" 
            :fields="table.fields"
            :filterIncludedFields="table.filterFields"
            :filter="table.filter"
            :no-provider-paging="true"
            :no-provider-sorting="true"
            :no-provider-filtering="true"
            @filtered="onFiltered"
            @sort-changed="onSorted"
        >
            <template v-slot:table-busy>
                <div class="text-center text-danger my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong class="ml-2">Loading...</strong>
                </div>
            </template>
        </b-table>

        <b-modal 
            id="modal-add"
            title="Add Server"
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
                    <span v-if="!postInProgress">Save</span>
                </b-button>
                <b-button variant="secondary" @click="cancel()">Cancel</b-button>
            </template>
        </b-modal>
    </div>
</Layout>
</template>

<script>
import { ValidationProvider, ValidationObserver, extend } from "vee-validate"
import { required, min, length } from "vee-validate/dist/rules"
import axios from "axios"
import Layout from "@/components/layout/Layout.vue"
import iconForScope from "@/components/ui/elements/iconForScope.vue"

extend("required", required)
extend("min", min)
extend("length", length)
extend("url", {
    validate: value => {
        const pattern =  /^(?:(?:https?|ftp):\/\/)?(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:\/\S*)?$/
        return pattern.test(value)
    },
    message: "This field must be a valid URL"
})



export default {
    name: "TheServers",
    components: {
        ValidationProvider,
        ValidationObserver,
        Layout,
        iconForScope
    },
    data: function () {
        return {
            postInProgress: false,
            refreshInProgress: false,
            table: {
                isBusy: false,
                filtered: "",
                totalRows: 0,
                currentPage: 1,
                perPage: 30,
                filterFields: ["name", "url"],
                fields: [
                    {
                        key: "id",
                        sortable: true
                    },
                    {
                        key: "name",
                        sortable: true
                    },
                    {
                        key: "url",
                        sortable: false
                    },
                    {
                        key: "authkey",
                        sortable: false
                    }
                ],
            },
            tableItems: [],
            serverForm: {
                name: "",
                url: "",
                skip_ssl: false,
                authkey: "",
                recursive_add: true
            },
            serverFormState: {
                name: null,
                url: null,
                authkey: null,
            }
        }
    },
    computed: {
    },
    methods: {
        onFiltered(filteredItems) {
            this.table.totalRows = filteredItems.length
            this.table.currentPage = 1
        },
        onSorted() {
            this.table.currentPage = 1
        },
        getValidationState({ dirty, validated, valid = null }) {
            return dirty || validated ? valid : null
        },
        resetModal() {
            this.serverForm.name = ""
            this.serverForm.url = ""
            this.serverForm.skip_ssl = false
            this.serverForm.authkey = ""
            this.serverForm.recursive_add = true
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
            const url = "http://127.0.0.1:5000/servers/add"
            let that = this
            axios.post(url, this.serverForm)
                .then((response) => {
                    this.$nextTick(() => {
                        this.$refs.observer.reset()
                    })
                    this.$nextTick(() => {
                        this.$bvModal.hide("modal-add")
                    })
                    that.$bvToast.toast(response, {
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
        },
        getIndex(ctx) {
            const url = "http://127.0.0.1:5000/servers/index?page=" + ctx.currentPage + "&size=" + ctx.perPage
            // let that = this

            let promise  = axios.get(url)
            return promise
                .then((response) => {
                    this.totalRows = response.data.length
                    this.items = response.data
                    return response.data
                }).catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch server index",
                        variant: "danger",
                    })
                    return []
                })

            // axios.get(url)
            //     .then(response => {
            //         callback(response.data)
            //         // callback(response.items)
            //     })
            //     .catch(error => {
            //         that.$bvToast.toast(error, {
            //             title: "Could not fetch server index",
            //             variant: "danger",
            //         })
            //         callback([])
            //     })
            // return null // Must return null or undefined to signal b-table that callback is being used


            // const promise = axios.get(url)
            // Must return a promise that resolves to an array of items
            // return promise
            //     .then(data => {
            //         // Pluck the array of items off our axios response
            //         const items = data.items
            //         // Must return an array of items or an empty array if an error occurred
            //         return items || []
            //     })
            //     .catch(error => {
            //         that.$bvToast.toast(error, {
            //             title: "Could not fetch server index",
            //             variant: "danger",
            //         })
            //         return []
            //     })
        }
    },
    
}
</script>

<style scoped>
</style>
