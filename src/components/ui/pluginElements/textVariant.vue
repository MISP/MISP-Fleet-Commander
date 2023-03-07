<template>
    <span :class="`text-${variant}`">{{ text }}</span>
</template>

<script>
export default {
    name: 'PluginElementTextVariant',
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
        variant() {
            return this.data.variant
        },
        text() {
            return this.data.text
        }
    },
}
</script>

<style scoped>
i.fa-check {
    color: green
}

i.fa-times {
    color: red
}
</style>
