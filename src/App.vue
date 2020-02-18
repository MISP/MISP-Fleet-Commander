<template>
    <div id="app">
        <component :is="layout">
            <router-view :layout.sync="layout"/>
        </component>
    </div>
</template>

<script>
export default {
    name: "App",
    data () {
        return {
            layout: "div" // fallback value if the layout is not set in the view
        }
    }
}
</script>
