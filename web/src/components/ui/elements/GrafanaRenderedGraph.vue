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
            grafana_base_url: 'http://localhost:3000',
            grafana_dashboard_data: 'render/d-solo/ce6olif96756od',
            grafana_other_params: {
                timezone: 'browser',
                theme: 'light',
                'var-bucket':  'MISP-Fleet-Commander',
            }
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
            const url_params_dict = JSON.parse(JSON.stringify(this.grafana_other_params))
            // url_params_dict['width'] = this.width
            // url_params_dict['height'] = this.height
            // url_params_dict['from'] = this.getFromDate
            // url_params_dict['to'] = this.getToDate
            // url_params_dict['var-instance'] = this.getInstanceName
            // url_params_dict['panelId'] = this.panelId
            // const url_params = new URLSearchParams(url_params_dict).toString()
            // return `${this.grafana_base_url}/${this.grafana_dashboard_data}?${url_params}`
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
            console.log('retryLoading');
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
            console.log('loadingRequested');
            if (newValue === false) {
                this.retryLoading()
            }
        }
    }

}
</script>

<style scoped>
</style>