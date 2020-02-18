<script>
import Vue from "vue"

export default {
    name: "Layout",
    props: {
        name: {
            type: String,
            required: true
        }
    },
    created () {
        // Check if the layout component
        // has already been registered.
        if (!Vue.options.components[this.name]) {
            Vue.component(
                this.name,
                () => import(`@/components/layout/${this.name}.vue`)
            )
        }

        this.$parent.$emit("update:layout", this.name)
    },
    render () {
        return this.$slots.default[0]
    }
}
</script>
