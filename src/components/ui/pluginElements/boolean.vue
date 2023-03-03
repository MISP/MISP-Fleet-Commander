<template>
    <i :class="['fa', data ? 'fa-check' : 'fa-times']"></i>
</template>

<script>
export default {
    name: 'PluginElementBoolean',
    props: {
        data: {
            type: Boolean,
            required: true
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
