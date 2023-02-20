<template>
    <b-modal 
        id="modal-delete-selected"
        title="Delete selected group"
        size="xl"
        scrollable
        @ok.prevent="handleSubmission"
    >

        <b-table-simple small bordered="false" :bordered="false" :borderless="true">
            <b-tbody>
                <b-tr>
                    <b-th>Group name</b-th>
                    <b-td>{{ getGroup.name }}</b-td>
                </b-tr>
                <b-tr>
                    <b-th>Description</b-th>
                    <b-td>{{ getGroup.description || '-- None --' }}</b-td>
                </b-tr>
                <b-tr>
                    <b-th>Server count</b-th>
                    <b-td>{{ getGroup.server_count }}</b-td>
                </b-tr>
            </b-tbody>
        </b-table-simple>

        <b-table-lite
            small 
            :fields="getServerFields"
            :items="getGroup.servers"
        >
        </b-table-lite>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="danger" @click="ok()" :disabled="postInProgress">
                <b-spinner 
                    small
                    v-if="postInProgress"
                ></b-spinner>
                <span class="sr-only">Deleting...</span>
                <span v-if="!postInProgress">Delete</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<script>
import { mapState } from "vuex"

export default {
    name: "DeleteSelectedModal",
    props: {
        group_id: {
            type: Number,
            required: true
        },
    },
    data: function() {
        return {
            postInProgress: false
        }
    },
    computed: {
        ...mapState({
            getSelectedServerGroup: state => state.serverGroups.selected,
            getServerGroups: state => state.serverGroups.all
        }),
        getGroup() {
            return this.getServerGroups[this.group_id] ?? {}
        },
        getServerFields() {
            return ['id', 'name', 'url']
        },
    },
    methods: {
        handleSubmission() {
            this.postInProgress = true
            const serverGroup = this.getGroup
            this.$store.dispatch("serverGroups/deleteServerGroup", this.getGroup)
                .then(() => {
                    this.$nextTick(() => {
                        this.$bvModal.hide("modal-delete-selected")
                    })
                    this.$bvToast.toast(`${serverGroup.name} has been successfully deleted`, {
                        title: `${serverGroup.name} deleted`,
                        variant: "success",
                    })
                    this.$emit("deletion-success", "done")
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: `Could not delete ${serverGroup.name}`,
                        variant: "danger",
                    })
                })
        },
    }
}
</script>

<style scoped>

</style>
