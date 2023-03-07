<template>
    <span
        v-if="status !== '' && status !== undefined"
        :class="statusOk ? 'text-success' : 'text-danger'"
    >
        <span :class="['fas', statusOk ? 'fa-check' : 'fa-times']"></span>
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
        },
        statusOk () {
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