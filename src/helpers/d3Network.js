/* eslint-disable no-unreachable */
import * as d3 from "d3"

export default {
    constructNetwork(containerId, containerBoundingRect, d3data, componentGenerator, eventHandlers) {
        const boundingRect = containerBoundingRect
        const nodeHeight = 300
        const nodeWidth = 350
        const width = boundingRect.width
        const height = boundingRect.height

        const svg = d3.select(containerId).append("svg")
            .attr("width", width)
            .attr("height", height)
        const container = svg.append("g")

        const simulation = d3.forceSimulation(d3data.nodes)
            .alphaDecay(0.35)
            // .alphaDecay(0.15)
            // .force("link", d3.forceLink(this.d3data.links).id(function(d) { return d.id }))
            .force("link", d3.forceLink(d3data.links).id(function(d) { return d.id }).distance(nodeWidth/2).strength(0.5))
            // .force("charge", d3.forceManyBody())
            // .force("charge", d3.forceManyBody().strength(-5000))
            .force("collide", d3.forceCollide(nodeWidth))
            .force("center", d3.forceCenter(width / 2, height / 2))

        const zoom = d3.zoom()
            .scaleExtent([.1, 4])
            .on("zoom", function() { container.attr("transform", d3.event.transform) })
        svg.call(zoom)

        const link = container.append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(d3data.links)
            .enter().append("line")
            .attr("class", "link")
            .attr("stroke", "#999")
            .attr("stroke-opacity", 0.6)
            .style("stroke-width", function(d) { return Math.sqrt(d.weight ? d.weight : 1) })

        const node = container.append("g")
            .attr("class", "nodes")
            .selectAll("div")
            .data(d3data.nodes)
            .enter().append("g")
            // eslint-disable-next-line no-unused-vars
            .on("click", function(node, index, nodes) {
                eventHandlers.nodeClick(node)
            })
            .call(drag(simulation))

        node.append("foreignObject")
            .attr("id", d => `node-${d.id}`)
            .attr("height", nodeHeight)
            .attr("width", nodeWidth)
            .classed("nodeFO", true)
            .append("xhtml:div")
            .attr("data-vue-component", (selection, index, htmlNodes) => {
                const htmlNode = htmlNodes[index]
                const vm = componentGenerator.nodeComponent(selection, htmlNode)
                resizeParentForeignObject(vm.$el)
            })

        simulation
            .nodes(d3data.nodes)
            .on("tick", () => {
                link
                    .attr("x1", d => d.source.x + getNodeHalfDimension(d3.select(`#node-${d.source.id}`).node(), "width"))
                    .attr("y1", d => d.source.y + getNodeHalfDimension(d3.select(`#node-${d.source.id}`).node(), "height"))
                    .attr("x2", d => d.target.x + getNodeHalfDimension(d3.select(`#node-${d.target.id}`).node(), "width"))
                    .attr("y2", d => d.target.y + getNodeHalfDimension(d3.select(`#node-${d.target.id}`).node(), "height"))

                node.attr("transform", d => "translate(" + d.x + "," + d.y + ")")
            })

        function drag(simulation) {
            function dragstarted(d) {
                if (d3.event.sourceEvent.button === 2) { // ignore right click
                    dragended(d)
                    return
                }
                if (!d3.event.active) simulation.alphaTarget(0.3).restart()
                d.fx = d.x
                d.fy = d.y
            }
            
            function dragged(d) {
                d.fx = d3.event.x
                d.fy = d3.event.y
            }
            
            function dragended(d) {
                if (!d3.event.active) simulation.alphaTarget(0)
                d.fx = null
                d.fy = null
            }

            // Add support of the drag handle
            function dragfilter() {
                const handleClass = "top-header"
                const maxDepth = 5
                for (let index = 0; index < maxDepth; index++) {
                    const node = d3.event.path[index]
                    if (node.classList !== undefined) {
                        if (node.classList.contains(handleClass)) {
                            return true
                        }
                    }
                }
                return false
            }
            
            return d3.drag()
                .filter(dragfilter)
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended)
        }

        // sync svgForeignObject dimensions with those of its html child 
        function resizeParentForeignObject(htmlNode) {
            const divBoundingRect = htmlNode.getBoundingClientRect()
            const parentSVG = htmlNode.closest("foreignObject.nodeFO")
            parentSVG.setAttribute("width", `${divBoundingRect.width}px`)
            parentSVG.setAttribute("height", `${divBoundingRect.height}px`)
        }

        function getNodeHalfDimension(node, dimension) {
            return node.getBBox()[dimension] / 2
        }
    }
}