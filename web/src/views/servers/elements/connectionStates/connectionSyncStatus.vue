<template>
    <span v-if="isValidConnection">
        <b-badge :variant="getVariant">
            <i :class="['fas', syncFlagSet ? 'fa-check' : 'fa-times']"></i>
        </b-badge>
    </span>
    <span v-else class="text-muted n-a">N/A</span>
</template>

<script>
export default {
    name: "connectionState_syncStatus",
    props: {
        connection: {
            type: Object,
            required: true
        },
    },
    data: function() {
        return {}
    },
    computed: {
        isValidConnection: function() {
            return this.connection.status.localVersion !== ""
        },
        getDestinationConnection: function() {
            return this.connection.destination || null
        },
        getUser: function() {
            return this.getDestinationConnection.connectionUser
        },
        syncFlagSet: function() {
            return this.getUser.sync_flag || null
        },
        getVariant: function() {
            return this.syncFlagSet ? 'success' : 'danger'
        },
    }
}
</script>

<style scoped>
.n-a {
    font-size: 88%;
}
</style>