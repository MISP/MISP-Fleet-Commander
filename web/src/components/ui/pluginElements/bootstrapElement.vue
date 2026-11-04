<template>
    <div>
        <component v-if="isAllowedComponent" :is="bsComponentName" v-bind="safeData">{{ getText }}</component>
        <span v-else>{{ getText }}</span>
    </div>
</template>

<script>
// Plugin responses are not trusted: only these presentational components and
// props may be rendered. Anything else (`b-link href="javascript:..."`, raw
// `onclick` attributes, ...) is dropped.
const ALLOWED_COMPONENTS = ['badge', 'alert', 'spinner', 'progress']
const ALLOWED_PROPS = ['variant', 'title', 'pill', 'size', 'label', 'value', 'max', 'show', 'striped', 'animated', 'small', 'type']

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
        isAllowedComponent() {
            return ALLOWED_COMPONENTS.includes(this.data.component)
        },
        bsComponentName() {
            return `b-${this.data.component}`
        },
        safeData() {
            return Object.fromEntries(
                Object.entries(this.data).filter(([key]) => ALLOWED_PROPS.includes(key))
            )
        },
        getText() {
            return this.data.text ?? ''
        },
    },
}
</script>

<style scoped>
</style>
