<template>
    <span :class="['mr-1', 'align-middle', 'text-nowrap', moreThanOneDay ? 'text-danger' : 'text-muted']" style="cursor: auto;">
        <i v-if="!noicon" :class="['far fa-clock', clockMarginClass]"></i>
        <small v-if="validTimestamp !== false" class="align-middle">
            {{ validTimestamp | moment(type) }}
        </small>
        <small v-else class="align-middle">
            never
        </small>
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
        },
        noicon: {
            type: Boolean,
            default: false
        },
        clockNoMargin: {
            type: Boolean,
            default: false
        }
    },
    computed: {
        validTimestamp() {
            return Number.isInteger(this.timestamp) ? this.timestamp : false
        },
        moreThanOneDay() {
            return (new Date()).getTime()/1000 - this.timestamp > 3600
        },
        clockMarginClass() {
            return this.clockNoMargin ? "" : "mr-1"
        }
    }
}
</script>

<style scoped>

</style>