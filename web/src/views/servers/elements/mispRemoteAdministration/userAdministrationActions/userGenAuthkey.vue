<template>
    <b-modal
        id="modal-administration-user-gen-authkey"
        :title="`Generate Authentication Key for User`"
        @ok="genAuthkey"
    >
        <p class="my-4">Confirm adding authentication key for user: <pre>{{ user.User.email }}</pre></p>

        <template v-slot:modal-footer="{ ok, cancel }">
            <div v-show="!generatedKey.length">
                <b-button class="m-1" variant="primary" @click="ok()" :disabled="requestInProgress">
                    <b-spinner 
                        small
                        v-if="requestInProgress"
                    ></b-spinner>
                    <span class="sr-only">Saving...</span>
                    <span v-if="!requestInProgress">Generate AuthKey</span>
                </b-button>
                <b-button class="m-1" variant="secondary" @click="cancel()">Cancel</b-button>
            </div>
            <b-button
                v-show="generatedKey.length"
                variant="primary" @click="cancel()"
            >I have noted the key</b-button>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/userAdministration"

export default {
    name: "UserGenAuthkey",
    components: {
    },
    props: {
        user: {
            required: true,
            type: Object
        },
        server: {
            required: true,
            type: Object
        },
    },
    data: function() {
        return {
            requestInProgress: false,
            generatedKey: '',
        }
    },
    computed: {
    },
    methods: {
        genAuthkey(evt) {
            evt.preventDefault()
            this.requestInProgress = true
            api.genAuthkey(
                this.server.id,
                this.user.User.id,
                (data) => {
                    if (data.error !== undefined) {
                        this.$bvToast.toast(`Error while trying to generate authkey`, {
                            title: data.error,
                            variant: "danger",
                            solid: true
                        })
                    } else {
                        this.$bvToast.toast(`Successfully generated authkey`, {
                            title: 'Take note of the key before closing the modal.',
                            variant: "success",
                            solid: true
                        })
                        this.generatedKey = data
                    }
                    this.requestInProgress = false
                },
                (error) => {
                    this.$bvToast.toast(`Error while trying to generate authkey`, {
                        title: error,
                        variant: "danger",
                        solid: true
                    })
                    this.requestInProgress = false
                }
            )
        }
    }
}
</script>

<style>

</style>