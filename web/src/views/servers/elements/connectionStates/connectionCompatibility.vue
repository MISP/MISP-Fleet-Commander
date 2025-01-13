<template>
    <span v-if="isValidConnection" >
        <b-badge :variant="getColorVariant">
            <i :class="['fas', isCompatible ? 'fa-check' : 'fa-times']"></i>
        </b-badge>
        <span
        :class="['text-nowrap', `text-${getColorVariant}`]"
        >
            <span class="text-body"> {{ getText }}</span>
        </span>
    </span>
    <span v-else class="text-muted n-a">N/A</span>
</template>

<script>
export default {
    name: "connectionState_compatibility",
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
        getCompatibility: function() {
            return this.getStatus.compatibility || null
        },
        isCompatible: function() {
            return this.getCompatibility.message == "Compatible"
        },
        getColorVariant: function() {
            return this.getCompatibility.color || null
        },
        getText: function() {
            return this.getCompatibility.message || null
        },
    }
}
</script>

<style scoped>
.n-a {
    font-size: 88%;
}
</style>