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
        
        <b-table 
            striped hover 
            :items="getIndex" 
            :fields="fields"
        ></b-table>

        <b-modal 
            id="modal-add"
            title="Add Server"
            size="lg"
            @show="resetModal"
            @hidden="resetModal"
            @ok="handleOk"
        >
            <b-form ref="modalForm" @submit.stop.prevent="handleSubmit">
                <b-form-group
                    label="Server Name:"
                    label-for="input-name"
                    description="Local name of the server"
                    :state="serverFormState.name"
                    invalid-feedback="Name is required"
                >
                    <b-form-input
                        id="input-name"
                        v-model="serverForm.name"
                        placeholder="Enter Server Name"
                        :state="serverFormState.name"
                        required
                    ></b-form-input>
                </b-form-group>

                <b-form-group
                    label="Server URL:"
                    label-for="input-url"
                    description="The URL to access the server"
                    :state="serverFormState.url"
                >
                    <b-form-input
                        id="input-url"
                        v-model="serverForm.url"
                        required
                        placeholder="Enter Server URL"
                        :state="serverFormState.url"
                    ></b-form-input>
                </b-form-group>

                <b-form-group
                    label="User Authorization Key:"
                    label-for="input-authkey"
                    description="The AUTHKey or API Key of the user"
                    :state="serverFormState.authkey"
                >
                    <b-form-input
                        id="input-authkey"
                        v-model="serverForm.authkey"
                        required
                        placeholder="Enter User AUTHKey"
                        :state="serverFormState.authkey"
                    ></b-form-input>
                </b-form-group>

                <b-form-group
                    description="By checking this box, it will try to add other MISP Servers connected to this one using known remote Servers"
                >
                    <b-form-checkbox v-model="serverForm.recursiveAdd">Recursively Add Servers</b-form-checkbox>
                </b-form-group>
            </b-form>
        </b-modal>
    </div>
</Layout>
</template>

<script>
import Layout from "@/components/layout/Layout.vue"
import iconForScope from "@/components/ui/elements/iconForScope.vue"
import axios from "axios"

export default {
    name: "TheServers",
    components: {
        Layout,
        iconForScope
    },
    data: function () {
        return {
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
            serverForm: {
                name: "",
                url: "",
                authkey: "",
                recursiveAdd: true
            },
            serverFormState: {
                name: null,
                url: null,
                authkey: null,
                recursiveAdd: null
            }
        }
    },
    computed: {
    },
    methods: {
        resetModal() {
            this.serverForm.name = ""
            this.serverForm.url = ""
            this.serverForm.authkey = ""
            this.serverForm.recursiveAdd = true
        },
        handleOk(evt) {
            evt.preventDefault()
            this.handleSubmit()
        },
        handleSubmit() {
            // Exit when the form isn't valid
            if (!this.checkFormValidity()) {
                return
            }
            this.$nextTick(() => {
                this.$bvModal.hide("modal-add")
            })
        },
        checkFormValidity() {
            const valid = this.$refs.modalForm.checkValidity()
            this.nameState = valid
            return valid
        },
        getIndex(ctx, callback) {
            let url = "http://127.0.0.1:5000/servers/index?page=" + ctx.currentPage + "&size=" + ctx.perPage
            let that = this
            axios.get(url)
                .then(response => {
                    // callback(response.data)
                    callback(response.items)
                })
                .catch(error => {
                    that.$bvToast.toast(error, {
                        title: "Could not fetch server index",
                        variant: "danger",
                    })
                    callback([])
                })
            return null // Must return null or undefined to signal b-table that callback is being used


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
