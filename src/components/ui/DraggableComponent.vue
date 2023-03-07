<template>
    <div
        class="position-absolute"
        :style="{top: positions.top, right: positions.right, left: positions.left, bottom: positions.bottom}"
    >
        <slot />
    </div>
</template>

<script>
export default {
    name: "draggableComponent",
    props: {
        draggableContainer: {
            type: String,
        },
        handleClass: {  // class specifying the handle of for the drag. deafult: `draggableContainer`
            type: String,
        },
        positions: {
            type: Object,
            default: function() {
                return {top: "4em", left: "unset", right: "1em", bottom: "unset"}
            }
        }
    },
    data: function() {
        return {
            handleNode: null,
            origClientX: 0,
            origClientY: 0,
        }
    },
    methods: {
        enableDrag(e) {
            e = e || window.event
            e.preventDefault()
            this.origClientX = e.clientX
            this.origClientY = e.clientY
            document.onmouseup = this.disableDrag
            document.onmousemove = this.drag
        },
        disableDrag() {
            document.onmouseup = null
            document.onmousemove = null
        },
        drag(e) {
            e = e || window.event
            e.preventDefault()
            const dx = this.origClientX - e.clientX
            const dy = this.origClientY - e.clientY
            this.origClientX = e.clientX
            this.origClientY = e.clientY
            const left = this.$el.offsetLeft - dx
            const top = this.$el.offsetTop - dy
            let positions = {
                top: `${top}px`,
                left: `${left}px`,
                right: "unset",
                bottom: "unset"
            }
            this.$emit("update:positions", positions)
        },
        registerListeners() {
            if (this.handleNode === undefined) {
                this.$el.addEventListener("mousedown", this.enableDrag)
            } else if (this.handleNode !== null) {
                this.handleNode.addEventListener("mousedown", this.enableDrag)
            }
        },
        unRegisterListeners() {
            if (this.handleNode === undefined) {
                this.$el.removeEventListener("mousedown", this.enableDrag)
            } else if (this.handleNode !== null) {
                this.handleNode.removeEventListener("mousedown", this.enableDrag)
            }
        }
    },
    mounted() {
        this.$nextTick(function () {
            this.handleNode = document.getElementById(this.draggableContainer)
            if (this.handleClass !== undefined && this.handleNode !== null) {
                const handle = this.handleNode.querySelectorAll(this.handleClass)
                if (handle.length > 0) {
                    this.handleNode = handle[0]
                }
            }
            this.registerListeners()
        })
    },
    beforeDestroy() {
        this.unRegisterListeners()
    }
}
</script>

<style scoped>

</style>