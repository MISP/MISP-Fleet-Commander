<template>
    <div class="sidebar-container sidebar-collapsed">
        <ul class="sidebar-list">
            <li 
                class="sidebar-item"
                v-for="item in items"
                v-bind:key="item.name"
            >
                <router-link
                    :class="{'sidebar-link text-decoration-none': true, 'inactive': !canBeAccessed(item)}"
                    v-b-tooltip.hover.right
                    :title="!canBeAccessed(item) ? 'No fleet selected' : ''"
                    :to="item.to"
                >
                    <span class="icon">
                        <iconForScope :scope="item.scope"></iconForScope>
                    </span>
                    <span class="link-text text-nowrap">{{ item.name }}</span>
                </router-link>
            </li>
        </ul>
    </div>
</template>

<script>
import { mapGetters } from "vuex"
import iconForScope from "@/components/ui/elements/iconForScope.vue"

export default {
    name: "TheSideBar",
    components: {
        iconForScope
    },
    data: function () {
        return {
            items: [
                {
                    name: "Home",
                    to: { name: "home" },
                    scope: "home"
                },
                {
                    name: "MISP Servers",
                    to: { name: "servers.index" },
                    scope: "servers"
                },
                {
                    name: "MISP Connections",
                    to: { name: "connections" },
                    scope: "connections"
                },
                {
                    name: "Strategic View",
                    to: { name: "strategicView" },
                    scope: "strategicView"
                },
                {
                    name: "Users",
                    to: { name: "users" },
                    scope: "users"
                }
            ]
        }
    },
    props: {
    },
    computed: {
        ...mapGetters({
            selectedServerGroup: "serverGroups/selectedServerGroup"
        }),
    },
    methods: {
        canBeAccessed(item) {
            const { route } = this.$router.resolve({
                name: item.to.name,
            })
            if ([route].some(record => record.meta.requiresServerGroup)) {
                if (this.selectedServerGroup === null) {
                    return false
                } else {
                    return true
                }
            } else {
                return true
            }
        }
    },
}
</script>

<style scoped>
.sidebar-collapsed {
    width: 50px !important;
}

.sidebar-container {
    background-color: var(--var-color-yankeesblue);
    height: 100vh;
    padding-top: 20px;
    position: relative;
    -webkit-transition: width .2s;
    transition: width .2s;
    transition-timing-function: cubic-bezier(.23,1,.32,1);
}

.sidebar-container .collapse-container {
    bottom: 0;
    margin-bottom: 3.5rem;
}

.logo {
    max-height: 100px;
    margin-bottom: 20px;
}

.sidebar-list {
    list-style: none;
    padding-left: 0;
}

.sidebar-item {
    user-select: none;
    display: flex;
    justify-content: center;
}

.sidebar-item .router-link-active {
    background-color: var(--var-color-lapislazuli);
}

.sidebar-item a.router-link-active:before {
    content: " ";
    position: absolute;
    height: 100%;
    width: calc(2px + 0.3em);
    left: -0.3em;
    top: 0;
    background-color: var(--var-color-giantorgane);
}

.sidebar-item:hover {
    background-color: var(--var-color-charcoal);
}

.sidebar-link.inactive {
    filter: brightness(0.5);
    cursor: not-allowed;
}

.sidebar-link {
    display: block;
    padding: 10px 0;
    padding-left: calc(10px + 2px);
    padding-right: calc(10px - 2px);
    font-size: .9375rem;
    position: relative;
    -webkit-transition: left .2s;
    transition: left .2s;
    transition-timing-function: cubic-bezier(.23,1,.32,1);
    left: 0px;
}

.sidebar-link > span.icon {
    display: block;
    width: 30px;
    height: 30px;
}

.link-text {
    margin-left: 1em;
}

.sidebar-collapsed .link-text {
    display: none;
}

.sidebar-item:hover .sidebar-link:not(.inactive) {
    left: 0.2em;
}

.sidebar-link > .icon {
    color: white;
}

.sidebar-link img {
    width: 1em;
    height: 1em;
}

.sidebar-collapsed .sidebar-link > .icon {
    font-size: 1.5em;
}

.sidebar-collapsed .sidebar-link img {
    width: 1.5em;
    height: 1.5em;
}

.sidebar-collapse-button {
    display: block;
    color: white;
    padding: 15px 30px;
    align-items: center;

}

.sidebar-collapse-button:hover {
    background-color: var(--var-color-charcoal);
}

.sidebar-collapse-button .icon {
    transition: left .2s;
    transition-timing-function: ease;
    transition-timing-function: cubic-bezier(.23,1,.32,1);
    position: relative;
    left: 0px;
    font-size: 1.5em;
}

.sidebar-collapse-button:hover .icon {
    left: -0.3em;
}

.sidebar-collapse-button .icon > i:before {
    content: "\f100";
}

.sidebar-collapsed .sidebar-collapse-button:hover .icon {
    left: 0.3em;
}

.sidebar-collapsed .sidebar-collapse-button .icon > i:before {
    content: "\f101";
}
</style>