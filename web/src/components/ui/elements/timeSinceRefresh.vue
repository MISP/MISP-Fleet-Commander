<template>
    <span :class="['mr-1', 'align-middle', 'text-nowrap', noformat ? '' : (moreThanOneDay ? 'text-danger' : 'text-muted')]" style="cursor: auto;" :title="timestampTitle">
        <i v-if="!noicon" :class="['far fa-clock', clockMarginClass]"></i>
        <component 
            v-if="validTimestamp !== false && integerTimestamp !== 0" 
            :is="small ? 'small' : 'span'"
            class="align-middle"
        >
            {{ validTimestamp | moment(type) }}
        </component>
        <component
            v-else
            :is="small ? 'small' : 'span'"
            class="align-middle"
        >
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
        integerTimestamp() {
            const timestampValue = Number.parseInt(this.timestamp)
            return Number.isNaN(this.timestampValue) ? false : timestampValue
        },
        validTimestamp() {
            return Number.isInteger(this.integerTimestamp) ? this.integerTimestamp : false
        },
        moreThanOneDay() {
            return (new Date()).getTime()/1000 - this.integerTimestamp > 3600
        },
        clockMarginClass() {
            return this.clockNoMargin ? "" : "mr-1"
        },
        timestampDate() {
            return moment(this.integerTimestamp * 1000).format("ddd DD/MM/YYYY HH:mm")
        },
        timestampFromNow() {
            return moment(this.integerTimestamp * 1000).fromNow()
        },
        timestampTitle() {
            return this.type == "from" ? this.timestampDate : this.timestampFromNow
        }
    }
}
</script>

<style scoped>

</style>