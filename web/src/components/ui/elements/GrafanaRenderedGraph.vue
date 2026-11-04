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
            :src="imageSrc"
            :alt="graphAltTitle"
            :title="graphAltTitle"
            :width="width"
            :height="height"
        >
    </span>
</template>

<script>
import api from "@/api/servers"

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
            imageSrc: null,
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
        isImageLoaded: function() {
            return !this.loadingRequested && this.isLoaded
        },
    },
    methods: {
        imgLoaded() {
            this.isLoaded = true
        },
        loadImage() {
            const payload = {
                server_id: this.server.id,
                panel_id: this.panelId,
                from_time: this.getFromDate,
            }
            api.monitoringImage(payload, (blob) => {
                if (this.imageSrc !== null) {
                    URL.revokeObjectURL(this.imageSrc)
                }
                this.imageSrc = URL.createObjectURL(blob)
            }, () => {
                this.imgLoadingError()
            })
        },
        retryLoading() {
            this.loadImage()
        },
        imgLoadingError() {
            if (!this.retriedOnce) {
                this.retriedOnce = true
                this.retryLoading()
            } else {
                this.imgLoaded()
            }
        },
    },
    watch: {
        loadingRequested: function(newValue) {
            if (newValue === false) {
                this.retryLoading()
            }
        }
    },
    mounted() {
        this.loadImage()
    },
    beforeDestroy() {
        if (this.imageSrc !== null) {
            URL.revokeObjectURL(this.imageSrc)
        }
    }

}
</script>

<style scoped>
</style>