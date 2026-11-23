<script>
import Vue from "vue"

export default {
    name: "AppLayout",
    props: {
        name: {
            type: String,
            required: true
        }
    },
    created () {
        // Tells App which layout the page expects. App draws the one its route gives (meta.layout, see
        // helpers/layouts.js) and only checks this one against it
        // Check if the layout component
        // has already been registered.
        // if (!Vue.options.components[this.name]) {
        //     Vue.component(
        //         this.name,
        //         () => import(`@/components/layout/${this.name}.vue`)
        //     )
        // }
        this.$parent.$emit("update:layout", this.name)
    },
    render () {
        // The slot can be empty while a view (re-)renders: render nothing rather than throw
        return (this.$slots.default || [])[0]
    }
}
</script>
