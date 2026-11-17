<template>
    <b-modal
        id="modal-sharing-group-delete"
        :title="group ? `Delete ${group.name}?` : 'Delete the sharing group?'"
        @show="reset"
    >
        <div v-if="group" class="sg-delete">
            <p>
                <strong>{{ group.name }}</strong> is deleted from {{ server.name }}, with its member and server lists.
                It cannot be undone; other servers keep their copy.
            </p>
            <p v-if="usage.loading" class="usage muted"><i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> Checking whether events use it…</p>
            <b-alert v-else-if="usage.events > 0" show variant="warning" class="usage-alert">
                {{ usage.events }} event{{ usage.events === 1 ? " is" : "s are" }} shared with it: MISP refuses to delete it.
                Share {{ usage.events === 1 ? "that event" : "those events" }} differently first.
            </b-alert>
            <p v-else class="usage muted">
                <template v-if="usage.events === 0">No event is shared with it.</template>
                <template v-else>Could not count the events that use it.</template>
                MISP still refuses if attributes, objects or reports of other events use it.
            </p>
            <b-alert :show="error !== null" variant="danger" class="usage-alert">{{ error }}</b-alert>
        </div>
        <template #modal-footer="{ cancel }">
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
            <b-button variant="danger" :disabled="deleting || usage.loading || usage.events > 0" @click="remove">
                <b-spinner v-if="deleting" small class="mr-1"></b-spinner>Delete
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/sharingGroups"

export default {
    name: "SharingGroupDeleteModal",
    props: {
        server: {
            type: Object,
            required: true,
        },
        group: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            usage: { loading: false, events: null },
            deleting: false,
            error: null,
        }
    },
    methods: {
        reset() {
            this.deleting = false
            this.error = null
            this.usage = { loading: true, events: null }
            const group = this.group
            api.usage(this.server.id, group.id)
                .then((data) => { this.usage = { loading: false, events: data.events } })
                .catch(() => { this.usage = { loading: false, events: null } })
        },
        remove() {
            this.deleting = true
            this.error = null
            const name = this.group.name
            api.remove(this.server.id, this.group.uuid, name)
                .then(() => {
                    this.$bvToast.toast(`${name} was deleted from ${this.server.name}`, {
                        title: "Sharing group deleted",
                        variant: "success",
                        solid: true,
                    })
                    this.$emit("deleted", this.group)
                    this.$bvModal.hide("modal-sharing-group-delete")
                })
                .catch((error) => { this.error = error.message })
                .finally(() => { this.deleting = false })
        },
    },
}
</script>

<style scoped>
.sg-delete {
    font-size: 0.875rem;
    color: var(--var-color-yankeesblue);
}

.usage {
    margin-bottom: 0;
}

.muted {
    color: #6c757d;
}

.usage-alert {
    margin: 0.5rem 0 0;
}
</style>
