import * as d3 from "d3"

const LEVEL_LABELS = {
    ok: "Link OK",
    degraded: "Degraded link",
    broken: "Broken link",
    unknown: "Link not tested",
}
const LEVEL_ICONS = {
    degraded: "fa-exclamation",
    broken: "fa-times",
    unknown: "fa-question",
}

export default {
    constructNetwork(svgNode, networkContainer, d3data, componentGenerator, eventHandlers, callbacks) {
        const containerBoundingRect = networkContainer.getBoundingClientRect()
        const boundingRect = containerBoundingRect
        const nodeHeight = 300
        const nodeWidth = 350
        const width = boundingRect.width
        const height = boundingRect.height

        const linkColor = '#bcc0c2'
        const movingMarkerColor = '#2ca1db'
        const endMarkerSize = 4
        const linkBadgeStartOffset = 35

        let selectedLink = null
        let zoomLevel = 1
        // `{links: Set(vid), nodes: Set(id)}`: everything else is dimmed. null: nothing is
        let focus = null

        const generatedMarkerColors = []

        const allowLinkAnimation = false

        const svg = d3.select(svgNode)
            .attr("width", width)
            .attr("height", height)
            .on("click", function(e, d){
                unselectLink()
                eventHandlers.canvasClicked()
            })
        d3.select(window).on('resize.updatesvg', () => {
            const x = networkContainer.getBoundingClientRect().width
            const y = networkContainer.getBoundingClientRect().height
            svg
                .attr("width", x)
                .attr("height", y)
        })
        const container = svg.append("g").attr("class", "zoomContainer")

        // const simulation = d3.forceSimulation(d3data.nodes)
        //     .alphaDecay(0.35)
        //     // .alphaDecay(0.15)
        //     // .force("link", d3.forceLink(this.d3data.links).id(function(d) { return d.id }))
        //     .force("link", d3.forceLink(d3data.links).id(function(d) { return d.id }).distance(nodeWidth/2).strength(0.5))
        //     // .force("link", d3.forceLink(d3data.links).id(function(d) { return d.id }).distance(nodeWidth/2).strength((d) => d._managed_server ? 0.2 : 0.8))
        //     // .force("link", d3.forceLink(d3data.links).id(function(d) { return d.id }).distance((d) => d._managed_server ? nodeWidth : nodeWidth/10).strength(0.5))
        //     // .force("charge", d3.forceManyBody())
        //     // .force("charge", d3.forceManyBody().strength(-5000))
        //     .force("collide", d3.forceCollide(nodeWidth))
        //     // .force("collide", d3.forceCollide((d) => d._managed_server ? 2*nodeWidth : nodeWidth/4))
        //     .force("center", d3.forceCenter(width / 2, height / 2))

        // const simulation = d3.forceSimulation(d3data.nodes)
        //     .alphaDecay(0.35)
        //     .force("link", d3.forceLink(d3data.links).id(function(d) { return d.id }).distance(nodeWidth/2))
        //     .force("charge", d3.forceManyBody().strength(-3000))
        //     .force("collide", d3.forceCollide((d) => d._managed_server ? 0.9*nodeWidth : 0.3).iterations(3))
        //     .force("center", d3.forceCenter(width / 2, height / 2))

        const simulation = d3.forceSimulation(d3data.nodes)
            .alphaDecay(0.35)
            .force("link", d3.forceLink(d3data.links).id((d) => { return d.id }).distance(nodeWidth / 2))
            .force("charge", d3.forceManyBody().strength(-3000))
            .force("collide", d3.forceCollide((d) => d._managed_server ? 0.9*nodeWidth : 0.3*nodeWidth).strength(0.5) .iterations(1))
            .force("center", d3.forceCenter(width / 2, height / 2).strength(0.05))

        const zoom = d3.zoom()
            .scaleExtent([.08, 4])
            .on("zoom", function (event) {
                container.attr("transform", event.transform)
                event.transform.k_changed = zoomLevel != event.transform.k
                zoomLevel = event.transform.k
                
            })
            .on("end", function (event) {
                eventHandlers.refreshMinimap()
                eventHandlers.updateScale(event.transform)
                if (event.transform.k_changed) {
                    simulation.alphaTarget(0.001).restart()
                }
                
                // setTimeout(() => {
                //     simulation.alphaTarget(0)
                // }, 1)
            })
        svg.call(zoom)

        const defs = svg.append('defs')

        const linkGroup = container.append("g")
            .attr("class", "links")
        const markerGroup = container.append("g")
            .attr("class", "markers")
        const badgeGroup = container.append("g")
            .attr("class", "badges")
        const nodeGroup = container.append("g")
            .attr("class", "nodes")

        const markerDef = generateMarker('triangle', linkColor)

        let link
        let markers
        let node
        let badge

        updateData(d3data)
        genMarkersForAllKnownPathColor()

        function updateData(newData) {
            link = linkGroup
                .selectAll("path")
                .data(newData.links)
                .attr("class", function (d) {
                    return updateClassList('link', d)
                })

            const linkEnter = link
                .enter().append("path")
                .attr('id', (d) => `line_${d.vid}`)
                .attr('vid', (d) => d.vid)
                .on("click", function(event, d){
                    event.stopPropagation()
                    selectLink(event, d)
                    eventHandlers.linkClicked(d)
                })
                .attr("fill", "none")
                .attr("stroke", linkColor)
                .attr("stroke-linecap", 'round')
                .attr("stroke-opacity", 1)
                .attr("marker-end", 'url(#triangle)')
                .attr("class", function (d) {
                    return updateClassList('link', d)
                })
            linkEnter.append("title")

            link.exit().remove();
            link = linkEnter.merge(link)
            link.select("title").text(linkTitle)

            if (allowLinkAnimation) {
                markers = markerGroup
                    .selectAll("path")
                    .data(newData.links)
                    .attr("class", function (d) {
                        return updateClassList('marker', d)
                    })

                const markersEnter = markers
                    .enter().append("path")
                    .attr('id', (d) => `marker_${d.vid}`)
                    .attr('vid', (d) => d.vid)
                    .attr("class", function (d) {
                        return updateClassList('marker', d)
                    })
                    .attr('fill', "none")
                    .attr('stroke', (d) => movingMarkerColor)
                    .attr('stroke-opacity', 0.7)
                    .attr('stroke-linecap', "round")
                    .attr('stroke-width', "5")
                    .attr('stroke-dashoffset', "0")
                    .attr('stroke-dasharray', "16,150")
                markersEnter
                    .append('animate')
                    .attr('attributeName', 'stroke-dashoffset')
                    .attr('repeatCount', 'indefinite')
                    .attr('dur', '30s')
                    .attr('values', '100%;0')
                markers.exit().remove();
                markers = markersEnter.merge(markers)
            }

            badge = badgeGroup
                .selectAll("foreignObject")
                .data(newData.links)
                .attr("class", function (d) {
                    return updateClassList('link-badge', d)
                })
            const badgeEnter = badge
                .enter().append("foreignObject")
                .attr('id', (d) => `badge_${d.vid}`)
                .attr('vid', (d) => d.vid)
                .attr("height", '24px')
                .attr("width", '120px')
                .attr("class", function (d) {
                    return updateClassList('link-badge', d)
                })
                .on("click", function(event, d) {
                    event.stopPropagation()
                    const pathNode = svgNode.querySelector(`.links path.link#line_${d.vid}`)
                    selectLink({target: pathNode}, d)
                    eventHandlers.linkClicked(d)
                })
            badgeEnter
                .append('xhtml:div')
                .append('div')
                .attr('class', 'badge-icons')

            badge.exit().remove();
            badge = badgeEnter.merge(badge)
            badge.select('div')
                .attr('class', function (d) { return getHTMLIconsFromLinkConfig(d) !== '' ? 'badge-container' : 'badge-empty' })
                .attr('title', linkTitle)
            badge.select('div.badge-icons')
                .html(getHTMLIconsFromLinkConfig)

            node = nodeGroup
                .selectAll("foreignObject")
                .data(newData.nodes)
            const nodeEnter = node.enter()
                .append("foreignObject")
                .attr("id", d => `node-${d.id}`)
                .attr("height", nodeHeight)
                .attr("width", nodeWidth)
                .classed("nodeFO", true)
                .on("click", function(event, node) {
                    event.stopPropagation()
                    eventHandlers.nodeClick(node)
                })
                .call(drag(simulation))
            nodeEnter.append("xhtml:div")
                .attr("data-vue-component", (selection, index, htmlNodes) => {
                    const d3Node = d3.select(`#node-${selection.id}`)
                    const d3SVGNode = svg.node()
                    const htmlNode = htmlNodes[index]
                    componentGenerator.genericNodeComponent(selection, htmlNode, d3Node, d3SVGNode)
                })
            node = nodeEnter.merge(node)
            applyFocus()
            updateMarkers()

            simulation 
                .nodes(newData.nodes)
                .on("tick", () => {
                    link
                        .attr("d", function(d) {
                            const { x1, y1, x2, y2, dr } = calcEdgePathCoordinate(d.source, d.target)
                            return "M" + x1 + "," + y1 + "A" + dr + "," + dr + " 0 0,1 " + x2 + "," + y2;
                        })
                    link
                        .attr("d", function(d) {
                            const intersection = getIntersection(d.source, d.target)
                            let { x1, y1, dr } = calcEdgePathCoordinate(d.source, d.target)
                            if (intersection !== null) {
                                return "M" + x1 + "," + y1 + "A" + dr + "," + dr + " 0 0,1 " + intersection.x2 + "," + intersection.y2;
                                // return "M" + intersection.x1 + "," + intersection.y1 + "A" + dr + "," + dr + " 0 0,1 " + intersection.x2 + "," + intersection.y2;
                            }
                        })
                    link
                        .attr('fake', (d, i, allPath) => {
                            try {
                                const path = allPath[i]
                                const originNode = d3.select(`#node-${d.origin.id}`).node()
                                const nodeBoxWith = getNodeHalfDimension(originNode, "width")*2
                                const nodeBoxHeight = getNodeHalfDimension(originNode, "height")*2

                                const pathLength = path.getTotalLength();
                                let midpointLength = pathLength * (linkBadgeStartOffset/100);
                                if (
                                    pathLength <= 1*nodeBoxHeight ||
                                    pathLength <= 1.5*nodeBoxWith
                                ) {
                                    if (pathLength <= nodeBoxWith / 2.5) { // #FIXME: Should consider if the other node is west/east, instead since physic simulation consider the node as a circle
                                        midpointLength = 0.99*pathLength
                                    } else {
                                        midpointLength = 0.55*pathLength
                                    }
                                }
                                const pointAtLength = path.getPointAtLength(midpointLength)

                                // const intersection = getIntersection(d.source, d.target)
                                // const { dr } = calcEdgePathCoordinate(d.source, d.target)
                                // const fakePath = document.createElementNS("http://www.w3.org/2000/svg", "path")
                                // const fakeD = "M" + intersection.x1 + "," + intersection.y1 + "A" + dr + "," + dr + " 0 0,1 " + intersection.x2 + "," + intersection.y2;
                                // fakePath.setAttribute('d', fakeD)
                                // const pathLength = fakePath.getTotalLength();
                                // let midpointLength = 0.20*pathLength
                                // const pointAtLength = fakePath.getPointAtLength(midpointLength)
    
                                const theBadge = d3.select(`#badge_${d.vid}`)
                                const badgeBoxTrueSize = theBadge.selectChildren().node().getBoundingClientRect()
                                
                                const adjustedBasedOnBadgeContaier = {
                                    x: pointAtLength.x - (1/zoomLevel)*badgeBoxTrueSize.width/2,
                                    y: pointAtLength.y - (1/zoomLevel)*badgeBoxTrueSize.height/2,
                                }
                                theBadge.attr("transform", d => "translate(" + adjustedBasedOnBadgeContaier.x + "," + adjustedBasedOnBadgeContaier.y + ")")
                            } catch (InvalidStateError) {
                                // no big deal. Simply ignore
                            }
                        })

                    if (allowLinkAnimation) {
                        markers
                            .attr("d", function(d) {
                                const { x1, y1, x2, y2, dr } = calcEdgePathCoordinate(d.source, d.target)
                                return "M" + x1 + "," + y1 + "A" + dr + "," + dr + " 0 0,1 " + x2 + "," + y2;
                            })
                            .attr("d", function(d) {
                                const intersection = getIntersection(d.source, d.target)
                                const { x1, y1, dr } = calcEdgePathCoordinate(d.source, d.target)
                                if (intersection !== null) {
                                    return "M" + x1 + "," + y1 + "A" + dr + "," + dr + " 0 0,1 " + intersection.x2 + "," + intersection.y2;
                                }
                            })
                    }

                    node.attr("transform", d => "translate(" + d.x + "," + d.y + ")")
                })
                .on("end", () => {
                    eventHandlers.refreshMinimap()
                })
                .on("end.init_simulation", () => {
                    eventHandlers.zoomFit()
                    simulation.on("end.init_simulation", null)
                    callbacks.simulationDone()
                })

        }

        return {
            svgSelection: svg,
            simulation: simulation,
            zoom: zoom,
            updateData: updateData,
            setFocus: setFocus,
            focusNode: focusNode,
        }

        function setFocus(newFocus) {
            focus = newFocus
            applyFocus()
        }

        function applyFocus() {
            if (link === undefined) {
                return
            }
            const dimLink = (d) => focus !== null && !focus.links.has(d.vid)
            link.classed('dimmed', dimLink)
            badge.classed('dimmed', dimLink)
            node.classed('dimmed', (d) => focus !== null && !focus.nodes.has(d.id))
        }

        // Center the view on a node and make it stand out for a moment
        function focusNode(nodeID) {
            const theNode = d3data.nodes.find(n => n.id === nodeID)
            const nodeElement = svgNode.querySelector(`#node-${CSS.escape(String(nodeID))}`)
            if (theNode === undefined || nodeElement === null) {
                return false
            }
            const box = nodeElement.getBBox()
            const scale = Math.max(zoomLevel, 0.6)
            const centerX = theNode.x + box.width / 2
            const centerY = theNode.y + box.height / 2
            const transform = d3.zoomIdentity
                .translate(svgNode.clientWidth / 2 - scale * centerX, svgNode.clientHeight / 2 - scale * centerY)
                .scale(scale)
            const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
            svg.transition().duration(reduceMotion ? 0 : 600).call(zoom.transform, transform)
            nodeElement.classList.remove('node-located')
            void nodeElement.getBBox() // Restarts the animation when the same node is located twice
            nodeElement.classList.add('node-located')
            setTimeout(() => nodeElement.classList.remove('node-located'), 2000)
            return true
        }

        function genMarkersForAllKnownPathColor() {
            svgNode.querySelectorAll('.links path.link').forEach(pathNode => {
                const strokeColor = document.defaultView.getComputedStyle(pathNode).stroke
                const triangleID = `triangle-${canonizeStrokeColor(strokeColor)}`
                generateMarker(triangleID, strokeColor)
                pathNode.setAttribute('marker-end', `url(#${triangleID})`)
            });
        }

        function updateMarkers() {
            svgNode.querySelectorAll('.links path.link').forEach(pathNode => {
                updateMarker({target: pathNode})
            })
        }

        function updateMarker(event) {
            const targetElement = event.target
            const strokeColor = document.defaultView.getComputedStyle(targetElement).stroke
            const triangleID = `triangle-${canonizeStrokeColor(strokeColor)}`
            generateMarker(triangleID, strokeColor)
            targetElement.setAttribute('marker-end', `url(#${triangleID})`)
        }

        function canonizeStrokeColor(color) {
            const reSpace = /(\s|\(|\))/gi
            const reComma = /,/gi
            return color.replaceAll(reSpace, '').replaceAll(reComma, '_')
        }

        function unselectLink() {
            selectedLink = null
            svgNode.querySelectorAll('.links path.link').forEach(pathNode => {
                pathNode.classList.remove('selected')
                unselectMarker(pathNode)
            })
            updateMarkers()
        }

        function selectLink(event, d) {
            unselectLink(event)
            selectedLink = d.vid
            const targetElement = event.target
            targetElement.classList.add('selected')
            updateMarker(event)
            selectMarker(targetElement)
        }

        function selectMarker(linkElement) {
            if (allowLinkAnimation) {
                const vid = linkElement.getAttribute('vid')
                svgNode.querySelector(`path.marker#marker_${vid}`).classList.add('selected')
            }
        }
        function unselectMarker(linkElement) {
            if (allowLinkAnimation) {
                const vid = linkElement.getAttribute('vid')
                svgNode.querySelector(`path.marker#marker_${vid}`).classList.remove('selected')
            }
        }

        function linkLevel(d) {
            return (d.health && d.health.level) || 'unknown'
        }

        function updateClassList(elemBaseClass, d) {
            let classes = [elemBaseClass, `link-${linkLevel(d)}`]
            if (d.health && d.health.disabled) {
                classes.push('link-unused')
            }
            if (focus !== null && !focus.links.has(d.vid)) {
                classes.push('dimmed')
            }
            if (d.vid == selectedLink) {
                classes.push('selected')
            }
            if (!d._managed_server) {
                classes.push('unmanaged_server')
            }
            if (d._has_rules) {
                classes.push('has_rules')
            }
            if (d._internal_sync) {
                classes.push('internal_sync')
            }
            return classes.join(' ')
        }

        function escapeHTML(text) {
            return String(text).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c])
        }

        // Shown on hover over the link and its badge: the health and why
        function linkTitle(d) {
            const level = linkLevel(d)
            const lines = [`${LEVEL_LABELS[level]}${d.health && d.health.disabled ? ' · unused (push, pull and caching off)' : ''}`]
            const reasons = (d.health && d.health.reasons) || []
            reasons.forEach(reason => lines.push(`- ${reason.message}`))
            return lines.join('\n')
        }

        function getHTMLIconsFromLinkConfig(d) {
            let icons = []
            const level = linkLevel(d)
            if (level !== 'ok') {
                icons.push(`<i class="fas ${LEVEL_ICONS[level]} badge-health badge-health-${level}" aria-hidden="true"></i>`)
            }
            const serverConnection = d.destination.Server
            if (serverConnection.push) {
                const enabledMechanism = [
                    '- Sightings: ' + (serverConnection.push_sightings ? '✓' : '×') + '\n',
                    '- Galaxy Clusters: ' + (serverConnection.push_galaxy_clusters ? '✓' : '×') + '\n',
                    '- Analyst data: ' + (serverConnection.push_analyst_data ? '✓' : '×'),
                ]
                if (serverConnection.push_sightings && serverConnection.push_galaxy_clusters && serverConnection.push_analyst_data) {
                    icons.push(`<span title="All PUSH mechanisms are enabled.\n${enabledMechanism.join('')}">\uf35b</span>`)
                } else {
                    icons.push(`<span title="PUSH is enabled. The following other elements will also be synchronized:\n${enabledMechanism.join('')}">\uf062</span>`)
                }
            }
            if (serverConnection.pull) {
                const enabledMechanism = [
                    '- Galaxy Clusters: ' + (serverConnection.pull_galaxy_clusters ? '✓' : '×') + '\n',
                    '- Analyst data: ' + (serverConnection.pull_analyst_data ? '✓' : '×'),
                ]
                if (serverConnection.pull_galaxy_clusters && serverConnection.pull_analyst_data) {
                    icons.push(`<span title="All PULL mechanisms are enabled.s\n${enabledMechanism.join('')}">\uf358</span>`)
                } else {
                    icons.push(`<span title="PULL is enabled. The following other elements will also be synchronized:\n${enabledMechanism.join('')}">\uf063</span>`)
                }
            }
            if (d._has_rules) {
                const rules = d.filtering_rules || {}
                icons.push(`<i class="fas fa-filter badge-rules" title="${escapeHTML(`Filtering rules: ${rules.push_rule_number || 0} on push, ${rules.pull_rule_number || 0} on pull`)}"></i>`)
            }
            if (d._internal_sync) {
                icons.push(`<i class="fas fa-building badge-internal" title="Internal sync: the remote belongs to the same organisation"></i>`)
            }
            return icons.join(' ')
        }

        function calcEdgePathCoordinate(source, target) {
            const dx = target.x - source.x,
                dy = target.y - source.y,
                dr = Math.sqrt(dx * dx + dy * dy)*2;
            const x1 = source.x + getNodeHalfDimension(d3.select(`#node-${source.id}`).node(), "width")
            const y1 = source.y + getNodeHalfDimension(d3.select(`#node-${source.id}`).node(), "height")
            const x2 = target.x + getNodeHalfDimension(d3.select(`#node-${target.id}`).node(), "width")
            const y2 = target.y + getNodeHalfDimension(d3.select(`#node-${target.id}`).node(), "height")
            return {
                x1: x1,
                x2: x2,
                y1: y1,
                y2: y2,
                dr: dr,
            }
        }

        function drag(simulation) {
            function dragstarted(event, d) {
                if (event.sourceEvent.button === 2) { // ignore right click
                    dragended(event, d)
                    return
                }
                if (!event.active) simulation.alphaTarget(0.3).restart()
                d.fx = event.x
                d.fy = event.y
            }
            
            function dragged(event, d) {
                d.fx = event.x
                d.fy = event.y
                simulation.alphaTarget(0.3).restart()
            }
            
            function dragended(event, d) {
                if (!event.active) simulation.alphaTarget(0)
                // d.fx = null
                // d.fy = null
                d.fx = event.x
                d.fy = event.y
            }

            // Add support of the drag handle
            function dragfilter(event) {
                const handleClass = "top-header"
                const maxDepth = 5
                let cElement = event.target
                for (let index = 0; index < maxDepth; index++) {
                    if (cElement.classList !== undefined) {
                        if (cElement.classList.contains(handleClass)) {
                            return true
                        }
                    }
                    cElement = cElement.parentElement
                }
                return false
            }
            
            return d3.drag()
                .filter(dragfilter)
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended)
        }

        function getNodeHalfDimension(node, dimension) {
            if (node !== null) {
                return node.getBBox()[dimension] / 2
            }
            return 100
        }

        function setAttrs(elem, attrs) {
            for (const k in attrs) {
                if (Object.prototype.hasOwnProperty.call(attrs, k)) {
                    const v = attrs[k];
                    elem.attr(k, v)
                }
            }
        }

        function generateMarker(id, fillColor) {
            if (generatedMarkerColors.includes(id)) {
                return
            }
            const definition = defs.append('marker')
            setAttrs(definition, {
                'id': id,
                'viewBox': '0 0 10 10',
                'markerWidth': endMarkerSize,
                'markerHeight': endMarkerSize,
                'refX': '1',
                'refY': '5',
                'markerUnits': 'strokeWidth',
                'orient': 'auto',
            })
            definition.append('path')
                .attr('d', 'M 0 0 L 10 5 L 0 10 z')
                .attr('fill', fillColor)
                .attr('opacity', 1)
            generatedMarkerColors.push(id)
            return definition
        }

        /*
            Functions below help compute the intersection between the link and the server's box.
            This is needed to ensure the path stops at the box's border instead of going to the center.
        */
        function Point(x, y) {
            if (!(this instanceof Point)) {
              return new Point(x, y)
            }
            this.x = x
            this.y = y
            Point.add = function (a, b) {
              return Point(a.x + b.x, a.y + b.y)
            }
            Point.sub = function (a, b) {
              return Point(a.x - b.x, a.y - b.y)
            }
            Point.cross = function (a, b) {
              return a.x * b.y - a.y * b.x;
            }
            Point.scale = function (a, k) {
              return Point(a.x * k, a.y * k)
            }
            Point.unit = function (a) {
              return Point.scale(a, 1 / Point.norm(a))
            }
            Point.norm = function (a) {
              return Math.sqrt(a.x * a.x + a.y * a.y)
            }
        }

        function pointInSegment([a, b], p) {
            return (
                Math.abs(Point.cross(Point.sub(p, a), Point.sub(b, a))) < 1e-6 &&
                Math.min(a.x, b.x) <= p.x && p.x <= Math.max(a.x, b.x) &&
                Math.min(a.y, b.y) <= p.y && p.y <= Math.max(a.y, b.y)
            );
        }
        
        function lineLineIntersection([a, b], [c, d]) {
            const v1 = Point.sub(b, a);
            const v2 = Point.sub(d, c);
            const kNum = Point.cross(Point.sub(c, a), Point.sub(d, c));
            const kDen = Point.cross(v1, v2);

            if (Math.abs(kDen) < 1e-6) return null; // Lines are parallel or coincident

            const scale = kNum / kDen;
            return Point.add(a, Point.scale(v1, Math.abs(scale)));
        }
        
        function segmentSegmentIntersection(s1, s2) {
            const ip = lineLineIntersection(s1, s2);
            return ip && pointInSegment(s1, ip) && pointInSegment(s2, ip) ? ip : null;
        }
        
        function boxSegmentIntersection(box, lineSegment) {
            const topLeft = new Point(box.x, box.y);
            const topRight = new Point(box.x + box.width, box.y);
            const bottomLeft = new Point(box.x, box.y + box.height);
            const bottomRight = new Point(box.x + box.width, box.y + box.height);

            const boxEdges = [
                [topLeft, topRight],  // Top
                [bottomLeft, bottomRight], // Bottom
                [topLeft, bottomLeft], // Left
                [topRight, bottomRight] // Right
            ];
        
            for (const edge of boxEdges) {
                const ip = segmentSegmentIntersection(edge, lineSegment);
                if (ip) return ip;
            }

            return null;
        }
        
        function boxCenter(box) {
            return new Point(box.x + box.width / 2, box.y + box.height / 2);
        }
        
        function buildSegmentThroughCenters(a, b) {
            return [boxCenter(a), boxCenter(b)];
        }
        
        function getIntersection(a, b) {
            a.width = getNodeHalfDimension(d3.select(`#node-${a.id}`).node(), "width") * 2;
            a.height = getNodeHalfDimension(d3.select(`#node-${a.id}`).node(), "height") * 2;
            b.width = getNodeHalfDimension(d3.select(`#node-${b.id}`).node(), "width") * 2;
            b.height = getNodeHalfDimension(d3.select(`#node-${b.id}`).node(), "height") * 2;

            const segment = buildSegmentThroughCenters(a, b);
            const ia = boxSegmentIntersection(a, segment);
            const ib = boxSegmentIntersection(b, segment);

            if (ia && ib) {
                const unitV = Point.unit(Point.sub(ib, ia));
                const k = 18; // Arrow width
                const adjustedIb = Point.sub(ib, Point.scale(unitV, k));

                return {
                    x1: ia.x,
                    y1: ia.y,
                    x2: adjustedIb.x,
                    y2: adjustedIb.y
                };
            }

            return null;
        }
    }
}