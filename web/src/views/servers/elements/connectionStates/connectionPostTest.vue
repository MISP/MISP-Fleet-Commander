<template>
    <span v-if="isValidConnection">
        <b-badge :variant="getColorVariant">
            <i :class="['fas', getPostSuccess ? 'fa-check' : 'fa-times']"></i>
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
    name: "connectionState_postTest",
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
        getPost: function() {
            return this.getStatus.post || null
        },
        getPostSuccess: function() {
            return this.getPost.success || null
        },
        getColorVariant: function() {
            return this.getPost.color || null
        },
        getText: function() {
            return this.getPost.result || null
        },
    }
}
</script>

<style scoped>
.n-a {
    font-size: 88%;
}
</style>