<template>
    <span>
        <pre v-if="isValidConnection" class="mb-0">{{ getVersion }}</pre>
        <span v-else class="text-muted n-a">N/A</span>
    </span>
</template>

<script>
export default {
    name: "connectionState_remoteVersion",
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
        getStatus: function() {
            return this.connection.status || null
        },
        getVersion: function() {
            return this.getStatus.remoteVersion || null
        },
    }
}
</script>

<style scoped>
pre {
    font-size: 100%;
}
.n-a {
    font-size: 88%;
}
</style>