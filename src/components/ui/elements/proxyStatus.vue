<template>
    <span
        v-if="proxy !== false"
        :class="proxy === true ? 'text-success' : 'text-danger'"
    >
        <span :class="['fas', proxy === true ? 'fa-check' : 'fa-times']"></span>
        {{ proxy === true ? '' : proxy }}
    </span>    
</template>

<script>
export default {
    name: "proxyStatus",
    props: {
        proxy: {
            default: function() {return false}
        }
    },
    computed: {
    },
    data: function() {
        return {}
    },
    methods: {
    }
}
</script>

<style scoped>

</style>