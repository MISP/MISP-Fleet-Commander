<template>
    <span :class="['mr-1', 'align-middle', 'text-nowrap', colourClass]" style="cursor: auto;" :title="fullTitle">
        <i v-if="!noicon" :class="['far fa-clock', clockMarginClass]"></i>
        <component 
            v-if="validTimestamp !== false && integerTimestamp !== 0" 
            :is="small ? 'small' : 'span'"
            class="align-middle"
            style="line-height: 1.2em;"
        >
            {{ timestampDynamicText }}
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
import { healthCellMixin, toneTextClass, toneTitle } from "@/helpers/healthCells"

export default {
    name: "timeSinceRefresh",
    mixins: [healthCellMixin],
    props: {
        // When the timestamp is a server's last refresh: coloured from its "data is out of date" issue
        server_id: {
            type: Number,
            default: null,
        },
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
    data() {
        return {
            interval: null,
            timestampDynamicText: '',
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
        moreThanOneHour() {
            return (new Date()).getTime()/1000 - this.integerTimestamp > 3600
        },
        staleTone() {
            return this.healthTone(this.server_id, "stale", { subject: "snapshot", content: false })
        },
        colourClass() {
            if (this.noformat) {
                return ""
            }
            if (this.staleTone !== null) {
                return toneTextClass(this.staleTone, "text-muted")
            }
            return this.moreThanOneHour ? "text-danger" : "text-muted"
        },
        fullTitle() {
            const why = toneTitle(this.staleTone)
            return why ? `${this.timestampTitle}\n${why}` : this.timestampTitle
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
    },
    methods: {
        genFromNow() {
            return moment(this.integerTimestamp * 1000).fromNow() 
        },
    },
    mounted() {
        this.timestampDynamicText = this.genFromNow()
        this.interval = setInterval(() => {
            this.timestampDynamicText = this.genFromNow();
        }, 3000)
    },
    beforeDestroy() {
        clearInterval(this.interval)
    }
}
</script>

<style scoped>

</style>