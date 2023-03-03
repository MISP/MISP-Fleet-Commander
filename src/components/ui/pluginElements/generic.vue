<template>
    <span>{{ data }}</span>
</template>

<script>
export default {
    name: 'PluginElementGeneric',
    props: {
        data: {
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
