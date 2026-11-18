// Colours and spacing shared by the usage charts. Series take the categorical slots in this order and never more
// than three per chart (validated on the white card surface; the third is under 3:1, so charts always carry a
// legend and a table view)
export const SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]

// Sequential ramp (blue, light → dark) for magnitudes such as the login heatmap
export const SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

export const INK = {
    primary: "#212d40",
    secondary: "#52514e",
    muted: "#6c757d",
    grid: "#eceef1",
    axis: "#c3c8d0",
    zero: "#f0f1f3",
    hover: "#eef3f9",
    spark: "#9aa6b5",
}

/** Keeps `width` at the plot element's rendered width (`ref="plot"`, else the root), for charts drawn in pixels */
export const widthMixin = {
    data() {
        return { width: 0 }
    },
    mounted() {
        this.measureWidth()
        if (typeof ResizeObserver !== "undefined") {
            this.widthObserver = new ResizeObserver(() => this.measureWidth())
            this.widthObserver.observe(this.$refs.plot || this.$el)
        }
    },
    beforeDestroy() {
        if (this.widthObserver) {
            this.widthObserver.disconnect()
        }
    },
    methods: {
        measureWidth() {
            const element = this.$refs.plot || this.$el
            this.width = element ? Math.floor(element.clientWidth) : 0
        },
    },
}
