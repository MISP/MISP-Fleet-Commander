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
import { mapState, mapGetters } from "vuex"

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
                        if (routeEntry.name == "servers.view") {
                            const server_id = that.$route.params[routeEntry.meta.breadcrumbs.textGetter]
                            bcItem = `${this.servers[server_id].name} [${server_id}]`
                        }
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
        ...mapState({
            servers: state => state.servers.servers,
        }),
    },
    methods: {
    }
}
</script>

<style scoped>
.breadcrumb-item + .breadcrumb-item::before {
    content: "\f0da";
    font-family: "Font Awesome 5 Free";
    font-weight: 900;
    -webkit-font-smoothing: antialiased;
    display: inline-block;
    font-style: normal;
    font-variant: normal;
    text-rendering: auto;
}
</style>
