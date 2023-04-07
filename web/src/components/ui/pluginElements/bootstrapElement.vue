<template>
    <div>
        <component :is="bsComponentName" v-bind="data">{{ getText }}</component>
    </div>
</template>

<script>
export default {
    name: 'PluginElementBootstrapElement',
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
        bsComponentName() {
            return `b-${this.data.component}`
        },
        getText() {
            return this.data.text ?? ''
        },
    },
}
</script>

<style scoped>
</style>
