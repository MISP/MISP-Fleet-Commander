<template>
    <div ref="minimapContainer" class="minimap-container overflow-visible">
        <svg ref="svgMap" class="overflow-visible">
            <g ref="minimap-group-container" class="minimap-group-container" fill="white" :transform="`translate(${minimapGroupPosition.x}, ${minimapGroupPosition.y})`">
                <g v-for="(node, index) in network.nodes" :key="index" :redrawCount="redrawCount">
                    <rect
                        v-bind="getRelativeNodePosition(node)"
                        :fill="server_status[node.id].error === undefined ? 'grey' : (server_status[node.id].error ? 'red' : 'green')"
                        :class="['server', selectedNode.id == node.id ? 'selected' : '']"
                    ></rect>
                </g>
            </g>
        </svg>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import * as d3 from "d3"

export default {
    name: "NetworkMinimap",
    props: {
        network: {
            type: Object,
            required: true
        },
        selectedNode: {
            type: Object,
            required: true
        },
        svgRootNode: {
            type: SVGSVGElement,
            required: true
        },
        networkSvgSelection: {
            required: true,
            type: Object
        },
        redrawCount: {
            type: Number,
            required: true
        },
        zoom: {
            required: true
        }
    },
    data: function() {
        return {
            svg: {
                width: "10vw",
                height: "10vh",
                realWidth: null,
                realHeight: null
            },
            viewPosition: {
                x: 5,
                y: 5,
                width: 10,
                height: 10
            },
            minimapGroupPosition: {
                x: 0,
                y: 0
            },
            brush: null
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
            connections: state => state.connections.all,
            server_status: state => state.servers.server_status,
            server_usage: state => state.servers.server_usage,
            remote_connections: state => state.servers.remote_connections,
        }),
    },
    methods: {
        extractNumberFromPixel(str) {
            return str.split("px")[0]
        },
        updateBrushPosition() {
            const transform = d3.zoomTransform(this.svgRootNode)
            const zoomContainer = this.svgRootNode.getElementsByClassName("zoomContainer")[0]
            const zoomBB = zoomContainer.getBBox()
            const zoomBCR = zoomContainer.getBoundingClientRect()
            const rootSvgBCR = this.svgRootNode.getBoundingClientRect()

            const svgDimension = this.getSVGDimension()
            const svgWidth = svgDimension.width
            const svgHeight = svgDimension.height

            // get the screen bounding box and convert into canvas space
            var screenLeft = -(zoomBCR.x - rootSvgBCR.x) / transform.k
            var screenWidth = rootSvgBCR.width / transform.k
            var screenTop = -(zoomBCR.y - rootSvgBCR.y) / transform.k
            var screenHeight = rootSvgBCR.height / transform.k

            // view can be used to adjust the screen dimension
            let viewLeft = screenLeft
            let viewWidth = screenWidth
            let viewTop = screenTop
            let viewHeight = screenHeight

            let viewXRatio = viewLeft / zoomBB.width
            let viewYRatio = viewTop / zoomBB.height
            let viewWidthRatio = viewWidth / zoomBB.width
            let viewHeightRatio = viewHeight / zoomBB.height

            this.viewPosition.x = viewXRatio * svgWidth * this.minimapGroupPosition.ratioX + this.minimapGroupPosition.x
            this.viewPosition.y = viewYRatio * svgHeight * this.minimapGroupPosition.ratioY + this.minimapGroupPosition.y
            this.viewPosition.width = viewWidthRatio * svgWidth * this.minimapGroupPosition.ratioX
            this.viewPosition.height = viewHeightRatio * svgHeight * this.minimapGroupPosition.ratioY

            // prevent overflowing to much and take care of padding from outer container
            const outerMinimapContainer = this.$refs["minimapContainer"].parentNode
            const outerMinimapContainerComputedStyle = getComputedStyle(outerMinimapContainer)
            const padding = parseInt(this.extractNumberFromPixel(outerMinimapContainerComputedStyle.padding))
            this.viewPosition.width = Math.max(
                Math.min(this.viewPosition.width + (this.viewPosition.x > 0 ? 0 : this.viewPosition.x - padding), svgWidth - this.viewPosition.x + padding),
                padding
            )
            this.viewPosition.x = Math.min(
                Math.max(this.viewPosition.x, -padding),
                svgWidth
            )
            this.viewPosition.height = Math.max(
                Math.min(this.viewPosition.height + (this.viewPosition.y > 0 ? 0 : this.viewPosition.y - padding), svgHeight - this.viewPosition.y + padding),
                padding
            )
            this.viewPosition.y = Math.min(
                Math.max(this.viewPosition.y, -padding),
                svgHeight
            )

            d3.select(this.$refs["svgMap"]).select(".brush")
                .call(this.brush.move, [[this.viewPosition.x, this.viewPosition.y], [this.viewPosition.x + this.viewPosition.width, this.viewPosition.y + this.viewPosition.height]])
        },
        getRelativeNodePosition(node) {
            if (this.$refs["svgMap"] !== undefined) {
                const svgMap = this.$refs["svgMap"].getBoundingClientRect()
                const svgWidth = svgMap.width
                const svgHeight = svgMap.height
                const zoomContainer = this.svgRootNode.getElementsByClassName("zoomContainer")[0]
                const zoomBB = zoomContainer.getBBox()
                const nodeBB = d3.select(`#node-${node.id}`).node().getBBox()
                
                const rectBaseWidth = nodeBB.width / zoomBB.width
                const rectBaseHeight = nodeBB.height / zoomBB.height

                const positionRatioZoomContainerX = (node.x - zoomBB.x) / zoomBB.width
                const positionRatioZoomContainerY = (node.y - zoomBB.y) / zoomBB.height

                let ratioX = 1, ratioY = 1
                let offsetX = 0, offsetY = 0
                if (zoomBB.width > zoomBB.height) {
                    ratioY = zoomBB.height / zoomBB.width
                    offsetY = svgMap.height / 2 - this.$refs["minimap-group-container"].getBoundingClientRect().height / 2
                } else {
                    ratioX = zoomBB.width / zoomBB.height
                    offsetX = svgMap.width / 2 - this.$refs["minimap-group-container"].getBoundingClientRect().width / 2
                }
                this.minimapGroupPosition.x = offsetX
                this.minimapGroupPosition.y = offsetY
                this.minimapGroupPosition.ratioX = ratioX
                this.minimapGroupPosition.ratioY = ratioY

                let nodePosition = {
                    x: positionRatioZoomContainerX * svgWidth * ratioX,
                    y: positionRatioZoomContainerY * svgHeight * ratioY,
                    width: rectBaseWidth * svgWidth * ratioX,
                    height: rectBaseHeight * svgHeight * ratioY
                }
                return nodePosition
            } else {
                return {x: 0, y: 0, width: 1, height: 1}
            }
        },
        zoomFit() {
            const zoomContainer = this.svgRootNode.getElementsByClassName("zoomContainer")[0]
            const zoomBounds = zoomContainer.getBBox()
            const rootSVG = this.svgRootNode
            const fullWidth = rootSVG.clientWidth
            const fullHeight = rootSVG.clientHeight
            const midX = zoomBounds.x + zoomBounds.width / 2
            const midY = zoomBounds.y + zoomBounds.height / 2
            if (zoomBounds.width == 0 || zoomBounds.height == 0) {
                return // nothing to fit
            }
            let scale = 1 / Math.max(zoomBounds.width / fullWidth, zoomBounds.height / fullHeight)
            scale *= 0.9 // zoom out a bit more
            var translateX = fullWidth / 2 - scale * midX
            var translateY = fullHeight / 2 - scale * midY
            this.moveZoom(translateX, translateY, scale)
        },
        handleMinimapMouseClick(mouseCoord) {
            const transform = d3.zoomTransform(this.svgRootNode)
            const zoomContainer = this.svgRootNode.getElementsByClassName("zoomContainer")[0]
            const zoomBCR = zoomContainer.getBoundingClientRect()
            const zoomBB = zoomContainer.getBBox()
            const svgDimension = this.getSVGDimension()
            const rootSvgBCR = this.svgRootNode.getBoundingClientRect()

            const absoluteX = mouseCoord[0]
            const absoluteY = mouseCoord[1]
            const relativeX = absoluteX / svgDimension.width
            const relativeY = absoluteY / svgDimension.height

            const px = zoomBCR.width - (1/this.minimapGroupPosition.ratioX) * relativeX * zoomBCR.width - rootSvgBCR.width/2
            const py = zoomBCR.height - (1/this.minimapGroupPosition.ratioY) * relativeY * zoomBCR.height - rootSvgBCR.height/2
            const x = 0
            const y = 0
            const p = [px, py]
            this.translateZoomTo(x, y, p)
        },
        getSVGDimension() {
            const svgMap = this.$refs["svgMap"]
            const svgMapBCR = this.$refs["svgMap"].getBoundingClientRect()
            let svgWidth = svgMapBCR.width
            let svgHeight = svgMapBCR.height
            const style = getComputedStyle(svgMap).transform
            const re = /matrix\((?<scale>[^)]+), 0, 0, 2.5, 0, 0\)/
            let reMatch = { groups: {scale: 1}}
            if (style.startsWith("matrix")) { // check if minimap is scaled through css
                reMatch = re.exec(style)
                svgWidth /= reMatch.groups.scale
                svgHeight /= reMatch.groups.scale
            }
            return { width: svgWidth, height: svgHeight, scale: reMatch.groups.scale }
        },
        moveZoom(x, y, k) {
            let zoomTransform = d3.zoomIdentity.translate(x, y)
            if (k !== undefined) {
                zoomTransform = zoomTransform.scale(k)
            }
            this.networkSvgSelection.transition()
                .duration(500)
                .call(this.zoom.transform, zoomTransform)
        },
        translateZoomBy(x, y) {
            this.zoom.translateBy(this.networkSvgSelection, x, y)
            // const zommTransform = d3.zoomIdentity.translateBy(x, y)
            // this.networkSvgSelection.transition()
            //     .duration(500)
            //     .call(this.zoom.transform, zommTransform)
        },
        translateZoomTo(x, y, p) {
            this.zoom.translateTo(this.networkSvgSelection, x, y, p)
            // const zommTransform = d3.zoomIdentity.translateBy(x, y)
            // this.networkSvgSelection.transition()
            //     .duration(500)
            //     .call(this.zoom.transform, zommTransform)
        },
        quickUpdate() {
            window.tzt = this.translateZoomTo
            this.$nextTick(() => {
                this.updateSVGRealDimension()
                this.updateBrushPosition()
            })
        },
        updateSVGRealDimension() {
            const svgMap = this.$refs["svgMap"].getBoundingClientRect()
            this.svg.realWidth = svgMap.width
            this.svg.realHeight = svgMap.height
        },
        initBrush() {
            const vm = this
            this.brush = d3.brush()
                .extent([[0, 0], [this.svg.realWidth, this.svg.realHeight]])
                .on("brush", null) // remove listener
                // .on("start", this.handleBrushStart)
                // .on("end", this.handleBrushEnd)
                // .on("brush", this.handleBrushDrag)

            d3.select(this.$refs["svgMap"]).append("g")
                .attr("class", "brush")
                .call(this.brush)
            d3.select(this.$refs["svgMap"]).select("g.brush")
                .attr("pointer-events", "none")

            d3.select(this.$refs["svgMap"]).on("click", function() {
                vm.handleMinimapMouseClick(d3.mouse(this))
            })
        },
        initAll() {
            window.moveZoom = this.moveZoom
            this.updateSVGRealDimension()
            this.initBrush()
        }
    },
    watch: {
        redrawCount: function () {
            this.quickUpdate()
        },
    },
    mounted: function() {
        this.$nextTick(() => {
            this.initAll()
        })
    }
}
</script>

<style scoped>
.minimap-container {
    width: 10vw;
    height: 10vh;
    background-color: white;
    /* transition: width 0.1s, height 0.1s ease-out; */
}

.minimap-container:hover {
    /* width: 25vw;
    height: 25vh; */
}

.minimap-container svg {
    width: 10vw;
    height: 10vh;
    /* transition: transform 0.1s ease-out; */
    transform-origin: top left;
}

.minimap-container:hover svg {
    /* transform: scale(2.5, 2.5); */
}

svg >>> .brush rect.selection {
    fill: #3578a0;
    fill-opacity: 0.1;
    shape-rendering: auto;
    stroke: #212d40;
    stroke-opacity: 0.3;
}

svg >>> .brush .handle {
    display: none;
}

svg >>> .brush .overlay {
    pointer-events: none;
}

rect.server {
}

rect.server.selected {
    stroke: black;
    stroke-width: 1px;
}
</style>