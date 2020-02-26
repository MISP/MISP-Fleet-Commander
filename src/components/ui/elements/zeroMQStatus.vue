<template>
    <span
        v-if="proxy !== false"
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
        status: {
            default: function() {
                return false
            }
        }
    },
    computed: {
        printable() {
            return this.status
            // return this.status == "not configured (so not tested)" ? true : this.status
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