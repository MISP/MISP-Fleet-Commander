<template>
    <div>
        <ServerNodeMicro
            v-if="scale < 0.2"
            :server="server"
            :d3Node="d3Node"
            :d3SVGNode="d3SVGNode"
        ></ServerNodeMicro>
        <ServerNodeMini
            v-else-if="scale < 0.5"
            :server="server"
            :d3Node="d3Node"
            :d3SVGNode="d3SVGNode"
        ></ServerNodeMini>
        <ServerNode
            v-else
            :scale="scale"
            :server="server"
            :d3Node="d3Node"
            :d3SVGNode="d3SVGNode"
        ></ServerNode>
    </div>
</template>

<script>
import ServerNode from "@/views/serverNetwork/elements/ServerNode.vue"
import ServerNodeMini from "@/views/serverNetwork/elements/ServerNodeMini.vue"
import ServerNodeMicro from "@/views/serverNetwork/elements/ServerNodeMicro.vue"

export default {
    name: "ServerNodeGeneric",
    components: {
        ServerNode,
        ServerNodeMini,
        ServerNodeMicro
    },
    props: {
        scaleInfo: {
            type: Object,
            required: true
        },
        server: {
            type: Object,
            required: true
        },
        d3Node: {
            type: Object,
            required: true
        },
        d3SVGNode: {
            type: SVGSVGElement,
            required: true
        }
    },
    data: function() {
        return {
        }
    },
    computed: {
        scale() {
            return this.scaleInfo.k
        }
    },
    mounted: function() {
    }
}
</script>

<style scoped>
</style>