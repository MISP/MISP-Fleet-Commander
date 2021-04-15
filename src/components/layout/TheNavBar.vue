<template>
    <div class="navbar-container">
        <b-navbar toggleable="lg" variant="light">
            <NavbarBreadcrumb></NavbarBreadcrumb>

            <b-navbar-nav class="ml-auto">
                <b-nav-text class="py-0 d-flex align-items-center">
                    <b-form-input 
                    v-model="searchText"
                    size="sm" class="m-0" placeholder="Search servers…"
                    ></b-form-input>
                </b-nav-text>

                <b-nav-item href="#">
                    <span class="fa fa-bell" title="Notifications"></span>
                </b-nav-item>

                <b-nav-item-dropdown right>
                    <template #button-content>
                        <iconButton
                            style="display: inline-block !important"
                            :text="serverGroupText"
                            icon="layer-group"
                            :tight="true"
                        ></iconButton>
                    </template>
                    <NavbarServerGroup></NavbarServerGroup>
                </b-nav-item-dropdown>
            </b-navbar-nav>
        </b-navbar>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import iconButton from "@/components/ui/elements/iconButton.vue"
import NavbarServerGroup from "@/components/layout/navbar/NavbarServerGroup.vue"
import NavbarBreadcrumb from "@/components/layout/navbar/NavbarBreadcrumb.vue"

export default {
    name: "TheNavBar",
    components: {
        iconButton,
        NavbarServerGroup,
        NavbarBreadcrumb,
    },
    data: function () {
        return {
            searchText: ""
        }
    },
    computed: {
        ...mapState({
            getSelectedServerGroup: state => state.serverGroups.selected,
        }),
        serverGroupText() {
            return this.getSelectedServerGroup !== null ? this.getSelectedServerGroup.name : "-no server group selected-"
        }
    }
}
</script>

<style scoped>
.navbar-container {
    /* border-bottom: 0; */
    box-shadow: 0 0 1.5rem 0 #212d402a;
    position: fixed;
    right: 0;
    left: 50px;
    z-index: 100;
}
</style>