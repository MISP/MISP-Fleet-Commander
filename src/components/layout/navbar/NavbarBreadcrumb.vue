<template>
    <div>
        <b-breadcrumb class="mb-0 p-0 bg-transparent d-flex align-items-center">
            <b-breadcrumb-item
                v-for="(item, index) in breadcrumbItems" :key="index"
                :to="item.to"
                :active="index === breadcrumbItems.length-1"
            >
                <img v-if="item.image_path"
                    :src="item.image_path"
                    :alt="item.alt"
                    class="icon-navbar"
                >
                <i v-else-if="item.icon" :class="`fa fa-${item.icon} mr-1`"></i>
                <span>{{ item.text }}</span>
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
                alt: "Application icon",
                image_path: require("@/assets/icon.png"),
                to: { name: "home" }
            })
            this.$route.matched.forEach(routeEntry => {
                if (routeEntry.meta.breadcrumbs) {
                    let bcItem
                    if (routeEntry.meta.breadcrumbs.textGetter) {
                        bcItem = that.$route.params[routeEntry.meta.breadcrumbs.textGetter]
                        if (routeEntry.name == "servers.view") {
                            const server_id = that.$route.params[routeEntry.meta.breadcrumbs.textGetter]
                            if (this.getServers[server_id]) {
                                bcItem = `${this.getServers[server_id].name} [${server_id}]`
                            } else {
                                bcItem = '?'
                            }
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
        getServers: function() {
            return this.servers || []
        },
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

.breadcrumb-item .icon-navbar {
    height: auto;
    width: 37px;
}
</style>
