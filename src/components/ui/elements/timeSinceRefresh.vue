<template>
    <span class="mr-1 text-muted" style="cursor: auto;">
        <template v-if="validTimestamp !== null">
            <i class="far fa-clock mr-1"></i>
            <small class="align-middle">
                    {{ timestamp | moment("from") }}
            </small>
        </template>
        <template v-else><i class="fas fa-question"></i></template>
    </span>
</template>

<script>
export default {
    name: "timeSinceRefresh",
    props: {
        timestamp: {
        }
    },
    computed: {
        validTimestamp() {
            return Number.isInteger(this.timestamp) ? this.timestamp : null
        }
    }
}
</script>

<style scoped>

</style>