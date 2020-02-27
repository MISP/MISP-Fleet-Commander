<template>
    <span
        v-if="proxy !== ''"
        :class="printable === true ? 'text-success' : 'text-danger'"
    >
        <span :class="['fas', printable === true ? 'fa-check' : 'fa-times']"></span>
        {{ printable === true ? '' : printable }}
    </span>    
</template>

<script>
export default {
    name: "proxyStatus",
    props: {
        proxy: {}
    },
    computed: {
        printable() {
            return this.proxy == "not configured (so not tested)" ? true : this.proxy
        }
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