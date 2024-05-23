<template>
    <i v-if="data === null" class="fa fa-question"></i>
    <i v-else :class="['fa', data ? 'fa-check' : 'fa-times']"></i>
</template>

<script>
export default {
    name: 'PluginElementBoolean',
    props: {
        data: {
            type: [Boolean, null],
            required: false
        },
        status: {
            required: false
        },
        errors: {
            required: false
        },
    }
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
