<template>
    <div v-html="getHtml"></div>
</template>

<script>
export default {
    name: 'PluginElementHtmlElement',
    props: {
        data: {
            type: Object,
            required: true
        },
        status: {
            required: false
        },
        errors: {
            required: false
        },
    },
    computed: {
        getHtml() {
            return this.data.html ?? 'No HTML returned'
        },
    },
}
</script>

<style scoped>
</style>
