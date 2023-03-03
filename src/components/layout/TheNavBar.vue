<template>
    <div class="navbar-container">
        <b-navbar toggleable="lg" variant="light">
            <NavbarBreadcrumb></NavbarBreadcrumb>

            <b-navbar-nav class="ml-auto">
                <b-nav-text class="py-0 d-flex align-items-center position-relative">
                    <b-form-input 
                    v-model="searchText"
                    @input="search"
                    @blur.native="revealSearch = !false"
                    @focus.native="revealSearch = true"
                    type="search"
                    size="sm" class="m-0" placeholder="Search servers…"
                    ></b-form-input>

                    <b-list-group
                        v-if="revealSearch && searchResults.length > 0"
                        class="position-absolute search-dd"
                        text="Search results"
                    >
                        <b-list-group-item
                            v-for="searchResult in searchResults"
                            :key="searchResult.id"
                            :to="{ name: 'servers.view', params: { server_id: searchResult.id } }"
                        >
                            <div class="d-flex flex-column">
                                <div class="d-flex">
                                    <span class="mr-2">{{ searchResult.name }}</span>
                                    <b class="ml-auto">{{ searchResult.server_group.name }}</b>
                                </div>
                                <span class="font-weight-light" style="font-size: smaller;">{{ searchResult.url }}</span>
                            </div>
                        </b-list-group-item>
                    </b-list-group>

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
import _debounce from 'lodash/debounce';
import { mapState, mapGetters } from "vuex"
import api from "@/api/common"

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
            revealSearch: false,
            searchText: "",
            searchResults: [],
        }
    },
    computed: {
        ...mapState({
            getSelectedServerGroup: state => state.serverGroups.selected,
        }),
        serverGroupText() {
            return this.getSelectedServerGroup !== null ? this.getSelectedServerGroup.name : "-no server group selected-"
        }
    },
    methods: {
        search: _debounce(
            function() {
                if (this.searchText.length > 0) {
                    this.doSearch()
                        .then(results => {
                            console.log(results);
                            this.searchResults = results
                        })
                        .catch(error => {
                            // this.searchResults = []
                            this.searchResults.splice(0, this.searchResults.length);
                        })
                } else {
                    // this.searchResults = []
                    this.searchResults.splice(0, this.searchResults.length);
                }
            }, 200
        ),

        doSearch() {
            return api.searchAll(
                this.searchText,
                error => {
                    this.$bvToast.toast(error, {
                        title: "Error while trying to search",
                        variant: "danger",
                    })
                }
            )
        },
    },
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

.search-dd {
    top: 105%;
    left: 0px;
    min-width: 20rem;
}
</style>