<template>
    <div>
        <div
            v-if="serverResponse.status_code"
            class="mb-0 d-flex"
        >
            <span class="font-weight-bold mr-1">
                <b-icon :class="status_response_class" icon="circle-fill"></b-icon>
                {{ serverResponse.status_code }}
                {{ serverResponse.reason }}
            </span>
            <span class="d-flex align-items-center text-muted smaller-text">
                <span class="mr-1">{{ elapsed_time_printable }}</span>
                <span>{{ content_length_printable }}</span>
            </span>
        </div>
        <div v-else>
            duh
        </div>
    </div>
</template>

<script>
import moment from "moment"
import Duration from "moment"

export default {
    name: "RequestResponseResult",
    props: {
        serverResponse: {
            type: Object,
            required: true,
        },
    },
    data: function() {
        return {
        }
    },
    computed: {
        status_response_class() {
            if (String(this.serverResponse.status_code) === "") {
                return "text-secondary"
            }
            if (String(this.serverResponse.status_code).startsWith("2")) {
                return "text-success"
            } else if (String(this.serverResponse.status_code).startsWith("5")) {
                return "text-danger"
            } else {
                return "text-warning"
            }
        },
        elapsed_time_printable() {
            let text = ""
            let serverReponseDuration
            if (Duration.isDuration(this.serverResponse.elapsed_time)) {
                serverReponseDuration = this.serverResponse.elapsed_time
            } else if (typeof this.serverResponse.elapsed_time === 'string' && this.serverResponse.elapsed_time !== "") {
                serverReponseDuration = moment.duration(moment(this.serverResponse.elapsed_time, 'H:mm:ss.SSSSSS').diff(moment(0, "HH")))
            } else {
                return text
            }
            text = `${serverReponseDuration.asMilliseconds()}ms`
            return text
        },
        content_length_printable() {
            let text = ""
            if (this.serverResponse.headers && this.serverResponse.headers['Content-Length'] !== undefined) {
                text = this.serverResponse.headers['Content-Length'] + " B"
                if (this.serverResponse.headers['Content-Length'] / (1024*1024) < 1) {
                    text = (this.serverResponse.headers['Content-Length'] / 1024).toFixed(2) + " kB"
                } else if (this.serverResponse.headers['Content-Length'] / (1024*1024*1024) < 1) {
                    text = (this.serverResponse.headers['Content-Length'] / (1024*1024)).toFixed(2) + " MB"
                }
            } else {
                text = ""
            }
            return text
        }
    },
    methods: {
    },
}
</script>

<style scoped>
    .smaller-text {
        font-size: 0.75em;
    }
</style>