<template>
    <span class="d-inline-block">
        <b-skeleton-img
            v-show="!isImageLoaded"
            no-aspect :width="`${width}px`" :height="`${height}px`"
            :animation="retriedOnce ? 'throb' : 'wave'"
        ></b-skeleton-img>
        <img
            v-show="isImageLoaded"
            @load="imgLoaded"
            @error="imgLoadingError"
            :src="getImageURL"
            :alt="graphAltTitle"
            :title="graphAltTitle"
            :width="width"
            :height="height"
        >
    </span>
</template>

<script>
export default {
    name: "GrafanaRenderedGraph",
    props: {
        panelId: {
            type: String,
            required: true,
        },
        server: {
            type: Object,
            required: true,
        },
        graphAltTitle: {
            type: String,
            required: false,
        },
        width: {
            type: Number,
            required: false,
            default: 200,
        },
        height: {
            type: Number,
            required: false,
            default: 150,
        },
        loadingRequested: {
            type: Boolean,
            required: false,
            default: false,
        }
    },
    data: function() {
        return {
            isLoaded: false,
            retriedOnce: false,
            cacheBuster: new Date().getTime(),
        }
    },
    computed: {
        getFromDate: function() {
            const one_hour = 60 * 60 * 1000
            return (new Date(new Date().getTime() - one_hour)).toISOString()
        },
        getToDate: function() {
            return (new Date()).toISOString()
        },
        getInstanceName: function() {
            return this.server.name
        },
        getImageURL: function() {
            return `http://127.0.0.1:5001/servers/monitoringImage/${this.server.id}/${this.panelId}/${this.getFromDate}?ts=${this.cacheBuster}`
        },
        isImageLoaded: function() {
            return !this.loadingRequested && this.isLoaded
        },
    },
    methods: {
        imgLoaded() {
            this.isLoaded = true
        },
        retryLoading() {
            // Changing the cache buster updates the `src` of the rendered image,
            // making the browser fetch it again. The template's `@load` / `@error`
            // handlers then reflect the outcome of that new attempt.
            this.cacheBuster = new Date().getTime()
        },
        imgLoadingError() {
            if (!this.retriedOnce) {
                this.retryLoading()
                this.retriedOnce = true
            }
        },
    },
    watch: {
        loadingRequested: function(newValue) {
            if (newValue === false) {
                this.retryLoading()
            }
        }
    }

}
</script>

<style scoped>
</style>