<template>
    <span
    >
        <b-badge :variant="getColorVariant">{{ getText }}</b-badge>
    </span>
</template>

<script>
export default {
    name: "connectionState_status",
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
        getStatus: function() {
            return this.connection.status.status || null
        },
        getCompatibility: function() {
            return this.connection.status.compatibility || null
        },
        getColorVariant: function() {
            return this.getCompatibility?.color ? this.getCompatibility.color : (this.getStatus.color || null)
        },
        getText: function() {
            return this.getStatus.message || null
        },
    }
}
</script>

<style scoped>
.badge {
    font-size: 88%;
}
</style>