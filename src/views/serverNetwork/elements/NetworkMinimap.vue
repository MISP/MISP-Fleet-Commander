<template>
    <div class="minimap-container">
        <svg v-if="svgRootNodeExists" ref="svgMap" @click="handleMinimapClick">
            <g ref="minimap-group-container" class="minimap-group-container" fill="white">
                <g v-for="(node, index) in network.nodes" :key="index" :redrawCount="redrawCount">
                    <rect
                        v-bind="getRelativeNodePosition(node)"
                        fill="red"
                    ></rect>
                </g>
                <rect
                    v-bind="viewPosition"
                    stroke-width="1px"
                    stroke="#0000ff"
                    fill="#0000ff11"
                ></rect>
            </g>
        </svg>
    </div>
</template>

<script>
import * as d3 from "d3"

export default {
    name: "NetworkMinimap",
    props: {
        network: {
            type: Object,
            required: true
        },
        networkSvgSelection: {
            required: true
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
                height: "10vh"
            },
            viewPosition: {
                x: 5,
                y: 5,
                width: 10,
                height: 10
            }
        }
    },
    computed: {
        svgRootNodeExists() {
            return this.networkSvgSelection !== null
        },
        svgNetworkNode() {
            return this.svgRootNodeExists ? this.networkSvgSelection.node() : null
        }
    },
    methods: {
        updateViewPosition() {
            const transform = d3.zoomTransform(this.svgNetworkNode)
            const zoomContainer = this.svgNetworkNode.getElementsByClassName("zoomContainer")[0]
            const zoomBB = zoomContainer.getBBox()
            const zoomBCR = zoomContainer.getBoundingClientRect()
            const rootSvgBCR = this.svgNetworkNode.getBoundingClientRect()

            const svgMap = this.$refs["svgMap"]
            const svgMapBCR = this.$refs["svgMap"].getBoundingClientRect()
            let svgWidth = svgMapBCR.width
            let svgHeight = svgMapBCR.height
            if (getComputedStyle(svgMap).transform.startsWith("matrix")) { // check if minimap is scaled through css
                svgWidth /= 2
                svgHeight /= 2
            }

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

            this.viewPosition.x = viewXRatio * svgWidth
            this.viewPosition.y = viewYRatio * svgHeight
            this.viewPosition.width = viewWidthRatio * svgWidth
            this.viewPosition.height = viewHeightRatio * svgHeight
        },
        getRelativeNodePosition(node) {
            if (this.svgNetworkNode !== null && this.$refs["svgMap"] !== undefined) {
                const svgMap = this.$refs["svgMap"].getBoundingClientRect()
                const svgWidth = svgMap.width
                const svgHeight = svgMap.height
                const svgNetworkTransform = d3.zoomTransform(this.svgNetworkNode)
                const zoomContainer = this.svgNetworkNode.getElementsByClassName("zoomContainer")[0]
                const zoomBB = zoomContainer.getBBox()
                const zoomBCR = zoomContainer.getBoundingClientRect()
                const nodeBCR = d3.select(`#node-${node.id}`).node().getBoundingClientRect()
                const nodeBB = d3.select(`#node-${node.id}`).node().getBBox()
                const rootSVGBoundingRect = this.svgNetworkNode.getBoundingClientRect()
                
                const rectBaseWidth = nodeBB.width / zoomBB.width
                const rectBaseHeight = nodeBB.height / zoomBB.height

                const maxX = Math.max(rootSVGBoundingRect.width, svgNetworkTransform.x + zoomBCR.width)
                const minX = Math.min(0, svgNetworkTransform.x)
                const maxY = Math.max(rootSVGBoundingRect.height, svgNetworkTransform.y + zoomBCR.height)
                const minY = Math.min(0, svgNetworkTransform.y)

                const positionRatioZoomContainerX = (node.x - zoomBB.x) / zoomBB.width
                const positionRatioZoomContainerY = (node.y - zoomBB.y) / zoomBB.height

                const positionRatioMaxX = (svgNetworkTransform.x + node.x * svgNetworkTransform.k) / maxX
                const positionRatioMaxY = (svgNetworkTransform.y + node.y * svgNetworkTransform.k) / maxY

                const positionRatioViewportX = (svgNetworkTransform.x + node.x * svgNetworkTransform.k) / rootSVGBoundingRect.width
                const positionRatioViewportY = (svgNetworkTransform.y + node.y * svgNetworkTransform.k) / rootSVGBoundingRect.height
                return {
                    x: positionRatioZoomContainerX * svgWidth,
                    y: positionRatioZoomContainerY * svgHeight,
                    width: rectBaseWidth * svgWidth,
                    height: rectBaseHeight * svgHeight
                }
            } else {
                return {x: 0, y: 0, width: 1, height: 1}
            }
        },
        handleMinimapClick(mouseEvent) {
            const svgMap = this.$refs["svgMap"].getBoundingClientRect()
            const relativeX = mouseEvent.clientX - svgMap.left
            const relativeY = mouseEvent.clientY - svgMap.top
            const ratioX = relativeX / svgMap.width
            const ratioY = relativeY / svgMap.height
            this.moveZoom(ratioX, ratioY)
        },
        moveZoom(ratioX, ratioY) {
            const svgNetworkTransform = d3.zoomTransform(this.svgNetworkNode)
            const zoomContainer = this.svgNetworkNode.getElementsByClassName("zoomContainer")[0]
            const zoomBCR = zoomContainer.getBoundingClientRect()
            const adaptedRatioX = 0.5 - ratioX
            const adaptedRatioY = 0.5 - ratioY
            const transX = adaptedRatioX * (zoomBCR.width)
            const transY = adaptedRatioY * (zoomBCR.height)
            const zommTransform = d3.zoomIdentity.scale(1).translate(transX, transY)
            // const zommTransform = d3.zoomIdentity.scale(svgNetworkTransform.k).translate(transX, transY)
            this.networkSvgSelection.transition()
                .duration(500)
                .call(this.zoom.transform, zommTransform)
                .on("end", () => {
                    // console.log("end")
                    // this.quickUpdate()
                })
        },
        quickUpdate() {
            this.$nextTick(() => {
                this.updateViewPosition()
            })
        }
    },
    watch: {
        redrawCount: function () {
            this.quickUpdate()
        },
    }
}
</script>

<style scoped>
.minimap-container {
    width: 10vw;
    height: 10vh;
    transition: width 0.1s, height 0.1s ease-out;
}

.minimap-container:hover {
    width: 20vw;
    height: 20vh;
}

.minimap-container svg {
    width: 10vw;
    height: 10vh;
    transition: transform 0.1s ease-out;
    transform-origin: top left;
}

.minimap-container:hover svg {
    transform: scale(2, 2);
}
</style>