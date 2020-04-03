<template>
    <div>
        <div ref="sparklineContainer" class="mx-auto sparklineContainer">
            <svg ref="sparklineSvg" :width="containerWidth" :height="containerHeight">
                <g>
                    <rect class="bar" v-for="item in data" :key="item[0]"
                        :x="x(item[0])"
                        :y="containerHeight - y(item[1])"
                        :width="barWidth"
                        :height="y(item[1])"
                        fill="MediumSeaGreen"
                        v-b-tooltip.html
                        :title="`${item[0]}, ${item[1]}`"
                    ></rect>
                </g>
            </svg>
        </div>
    </div>
</template>

<script>
import * as d3 from "d3"

export default {
    name: "SimpleBarChart",
    props: {
        data: {
            type: Array,
            required: true
        }
    },
    data: function() {
        return {
            svg: null,
            containerWidth: 250,
            containerHeight: 60,
            x: null,
            y: null,
        }
    },
    computed: {
        barWidth() {
            return (this.containerWidth - this.data.length) / this.data.length
        }
    },
    methods: {
    },
    created: function() {
        this.x = d3.scaleLinear()
            .domain(d3.extent(this.data, function(d) { return d[0] }))
            .range([0, this.containerWidth])
        this.y = d3.scaleLinear()
            .domain([0, d3.max(this.data, function(d) { return d[1] })])
            .range([ 0, this.containerHeight ])
    },
    mounted: function() {
    }
}
</script>

<style scoped>
.sparklineContainer {
    width: fit-content;
}

.containerCentered{
    
}
.bar {

}
</style>