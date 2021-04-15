<template>
    <div>
        <b-breadcrumb class="mb-0 p-0 bg-transparent">
            <b-breadcrumb-item
                v-for="(item, index) in breadcrumbItems" :key="index"
                :to="item.to"
                :active="index === breadcrumbItems.length-1"
            >
                <i v-if="item.icon" :class="`fa fa-${item.icon}`"></i>
                {{ item.text }}
            </b-breadcrumb-item>
        </b-breadcrumb>
    </div>
</template>

<script>

export default {
    name: "NavbarBreadcrumb",
    components: {
    },
    data: function () {
        return {
            
        }
    },
    computed: {
        breadcrumbItems() {
            const that = this
            let items = []
            items.push({
                text: "[Logo]",
                to: { name: "home" }
            })
            this.$route.matched.forEach(routeEntry => {
                if (routeEntry.meta.breadcrumbs) {
                    let bcItem
                    if (routeEntry.meta.breadcrumbs.textGetter) {
                        bcItem = that.$route.params[routeEntry.meta.breadcrumbs.textGetter]
                    } else {
                        bcItem = routeEntry.meta.breadcrumbs.text
                    }
                    items.push({
                        text: bcItem,
                        to: routeEntry.meta.breadcrumbs.to,
                        icon: routeEntry.meta.breadcrumbs.icon ? routeEntry.meta.breadcrumbs.icon : ""
                    })
                }
            })
            return items
        },
    },
    methods: {
    }
}
</script>

<style scoped>

</style>