<template>
    <div :class="['sidebar-container', sidebarCollapsed ? 'sidebar-collapsed' : '']">
        <ul class="sidebar-list">
            <li 
                class="sidebar-item"
                v-for="item in items"
                v-bind:key="item.name"
            >
                <router-link
                    class="sidebar-link text-decoration-none"
                    :to="item.to"
                >
                    <span class="icon">
                        <iconForScope :scope="item.scope"></iconForScope>
                    </span>
                    <span class="link-text text-nowrap">{{ item.name }}</span>
                </router-link>
            </li>
        </ul>
        <div class="collapse-container position-absolute w-100">
            <div
                class="d-flex justify-content-between align-middle sidebar-collapse-button useCursorPointer"
                @click="toggleSidebar"
            >
                <span class="link-text text-nowrap">Collapse sidebar</span>
                <span class="icon">
                    <i class="fa"></i>
                </span>
            </div>
        </div>
    </div>
</template>

<script>
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
                    to: { name: "servers" },
                    scope: "servers"
                },
                {
                    name: "MISP Network",
                    to: { name: "serverNetwork" },
                    scope: "serverNetwork"
                }
            ]
        }
    },
    props: {
        // selected_item: String,
    },
    computed: {
        sidebarCollapsed() {
            return this.$store.state.sidebarCollapsed
        }
    },
    methods: {
        toggleSidebar() {
            this.$store.commit("toggleSidebar")
        }
    }
}
</script>

<style scoped>
.sidebar-collapsed {
    width: 5em !important;
}

.sidebar-container {
    width: 15em;
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

.sidebar-item:hover {
    background-color: var(--var-color-charcoal);
}

.sidebar-link {
    display: block;
    padding: 15px 30px;
    font-size: .9375rem;
    position: relative;
    -webkit-transition: left .2s;
    transition: left .2s;
    transition-timing-function: cubic-bezier(.23,1,.32,1);
    left: 0px;
}

.link-text {
    margin-left: 1em;
}

.sidebar-collapsed .link-text {
    display: none;
}

.sidebar-link:hover {
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