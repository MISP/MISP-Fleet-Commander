<template>
    <span v-if="isValidConnection">
        {{ getUser.email }}
    </span>
    <span v-else class="text-muted n-a">N/A</span>
</template>

<script>
export default {
    name: "connectionState_user",
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
    }
}
</script>

<style scoped>
.n-a {
    font-size: 88%;
}
</style>