<template>
    <span :class="['text-nowrap', 'mr-1', moreThanOneDay ? 'text-danger' : 'text-muted']" style="cursor: auto;">
        <template>
            <i class="far fa-clock mr-1"></i>
            <small v-if="validTimestamp !== false" class="align-middle">
                {{ validTimestamp | moment(type) }}
            </small>
            <small v-else class="align-middle">
                never
            </small>
        </template>
    </span>
</template>

<script>
export default {
    name: "timeSinceRefresh",
    props: {
        timestamp: {
        },
        type: {
            default: "from"
        }
    },
    computed: {
        validTimestamp() {
            return Number.isInteger(this.timestamp) ? this.timestamp : false
        },
        moreThanOneDay() {
            return (new Date()).getTime()/1000 - this.timestamp > 3600
        }
    }
}
</script>

<style scoped>

</style>