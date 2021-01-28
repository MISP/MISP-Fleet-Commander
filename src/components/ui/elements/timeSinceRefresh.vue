<template>
    <span :class="['mr-1', 'align-middle', 'text-nowrap', noformat ? '' : (moreThanOneDay ? 'text-danger' : 'text-muted')]" style="cursor: auto;" :title="timestampTitle">
        <i v-if="!noicon" :class="['far fa-clock', clockMarginClass]"></i>
        <component :is="small ? 'small' : 'span'" v-if="validTimestamp !== false" class="align-middle">
            {{ validTimestamp | moment(type) }}
        </component>
        <component :is="small ? 'small' : 'span'" v-else class="align-middle">
            never
        </component>
    </span>
</template>

<script>
import moment from "moment"

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
        },
        noformat: {
            type: Boolean,
            default: false
        },
        small: {
            type: Boolean,
            default: true
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
        },
        timestampDate() {
            return moment(this.timestamp * 1000).format("ddd DD/MM/YYYY hh:mm")
        },
        timestampFromNow() {
            return moment(this.timestamp * 1000).fromNow()
        },
        timestampTitle() {
            return this.type == "from" ? this.timestampDate : this.timestampFromNow
        }
    }
}
</script>

<style scoped>

</style>