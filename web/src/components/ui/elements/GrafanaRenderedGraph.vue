<template>
    <span class="d-inline-block">
        <b-skeleton-img
            v-if="loadingRequested || (!isLoaded && !failed)"
            no-aspect :width="`${width}px`" :height="`${height}px`"
            :animation="retried ? 'throb' : 'wave'"
        ></b-skeleton-img>
        <span
            v-else-if="!isLoaded"
            class="graph-unavailable"
            :style="{ width: `${width}px`, height: `${height}px` }"
            :title="graphAltTitle"
        >
            <i class="fas fa-chart-area graph-unavailable-icon"></i>
            <span class="graph-unavailable-title">{{ graphAltTitle }}</span>
            <span>Graph unavailable</span>
        </span>
        <img
            v-show="isImageLoaded"
            v-if="imageURL !== null"
            @load="isLoaded = true"
            :src="imageURL"
            :alt="graphAltTitle"
            :title="graphAltTitle"
            :width="width"
            :height="height"
        >
    </span>
</template>

<script>
import { baseurl } from "@/api/apiConfig"
import common from "@/api/common"

const RETRY_DELAY_MS = 2000

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
            imageURL: null,
            isLoaded: false,
            retried: false,
            failed: false,
            retryTimer: null,
        }
    },
    computed: {
        imageEndpoint: function() {
            return `${baseurl}/servers/monitoringImage/${this.server.id}/${this.panelId}`
        },
        isImageLoaded: function() {
            return !this.loadingRequested && this.isLoaded
        },
    },
    methods: {
        loadImage() {
            clearTimeout(this.retryTimer)
            common.fetchImageObjectURL(this.imageEndpoint)
                .then((objectURL) => {
                    this.releaseImage()
                    this.imageURL = objectURL
                    this.failed = false
                })
                .catch(() => {
                    // The graph may not be rendered yet: try once more before giving up
                    if (!this.retried) {
                        this.retried = true
                        this.retryTimer = setTimeout(this.loadImage, RETRY_DELAY_MS)
                    } else {
                        this.failed = true
                    }
                })
        },
        releaseImage() {
            if (this.imageURL !== null) {
                URL.revokeObjectURL(this.imageURL)
            }
        },
    },
    watch: {
        loadingRequested: function(newValue) {
            if (newValue === false) {
                this.retried = false
                this.loadImage()
            }
        }
    },
    mounted() {
        this.loadImage()
    },
    beforeDestroy() {
        clearTimeout(this.retryTimer)
        this.releaseImage()
    },
}
</script>

<style scoped>
.graph-unavailable {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.15rem;
    padding: 0.5rem;
    border: 1px dashed #ced4da;
    border-radius: 0.25rem;
    background-color: #f8f9fa;
    color: #6c757d;
    font-size: 0.75rem;
    text-align: center;
    vertical-align: top;
}
.graph-unavailable-icon {
    font-size: 1.25rem;
    opacity: 0.6;
}
.graph-unavailable-title {
    font-weight: 600;
    color: #495057;
}
</style>
