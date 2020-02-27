<template>
    <span
        v-if="status !== ''"
        :class="printable === true ? 'text-success' : 'text-danger'"
    >
        <span :class="['fas', printable === true ? 'fa-check' : 'fa-times']"></span>
        {{ printable === true ? '' : printable }}
    </span>    
</template>

<script>
export default {
    name: "zeroMQStatus",
    props: {
        status: {}
    },
    computed: {
        printable() {
            return this.status !== ""
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