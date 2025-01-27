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
            const now = new Date().getTime()
            return `http://127.0.0.1:5001/servers/monitoringImage/${this.server.id}/${this.panelId}/${this.getFromDate}?ts=${now}`
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
            const that = this
            const img = new Image();
            img.src = this.getImageURL; // this should refer to the original failed image
            img.onerror = function() {
                that.imgLoaded()
            }
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