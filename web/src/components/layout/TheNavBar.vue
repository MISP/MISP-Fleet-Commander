<template>
    <div class="navbar-container">
        <b-navbar toggleable="lg" variant="light">
            <NavbarBreadcrumb></NavbarBreadcrumb>

            <b-navbar-nav class="ml-auto">
                <b-nav-text class="py-0 d-flex align-items-center position-relative">
                    <b-form-input 
                    v-model="searchText"
                    @input="search"
                    @blur.native="handleSearchInputBlur"
                    @focus.native="revealSearch = true"
                    type="search"
                    size="sm" class="m-0 global-search" placeholder="Search servers…"
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
                                    <span class="ml-auto">
                                        <img src="@/assets/fleet.svg" alt="Fleet icon" width="20" class="mr-1" style="filter: grayscale(1);">
                                        <b>{{ searchResult.fleet.name }}</b>
                                    </span>
                                </div>
                                <span class="font-weight-light" style="font-size: smaller;">{{ searchResult.url }}</span>
                            </div>
                        </b-list-group-item>
                    </b-list-group>

                </b-nav-text>

                <NavbarNotification></NavbarNotification>

                <b-dropdown right variant="secondary" toggle-class="secondary-soft">
                    <template #button-content>
                        <iconButton
                            style="display: inline-block !important;"
                            :text="fleetText"
                            icon="fleet"
                            use-asset
                            :tight="true"
                        ></iconButton>
                    </template>
                    <NavbarFleet></NavbarFleet>
                </b-dropdown>

                <template v-if="user">
                    <b-nav-item-dropdown right>
                        <template #button-content>
                            <iconButton
                                style="display: inline-block !important"
                                :text="user.email"
                                :tight="true"
                            ></iconButton>
                        </template>
                        <NavbarProfile></NavbarProfile>
                    </b-nav-item-dropdown>
                </template>

                <div class="d-flex align-items-center justify-content-center">
                    <b-button title="Settings" variant="outline-secondary" class="ml-1" size="sm" v-b-modal.modal-settings>
                        <i class="fa fa-cogs"></i>
                    </b-button>
                </div>

                <template v-if="!wsConnected">
                    <div title="Trying to connect websocket" class="d-flex align-items-center justify-content-center">
                        <img src="@/assets/websocket.svg" alt="Websocket icon" class="position-absolute" width="20" height="20">
                        <span>
                            <i class="fas fa-circle-notch fa-fw fa-spin text-muted" style="font-size: 32px;"></i>
                        </span>
                    </div>
                </template>

            </b-navbar-nav>
        </b-navbar>
    </div>
</template>

<script>
import _debounce from 'lodash/debounce';
import { mapState, mapGetters } from "vuex"
import api from "@/api/common"

import iconButton from "@/components/ui/elements/iconButton.vue"
import NavbarFleet from "@/components/layout/navbar/NavbarFleet.vue"
import NavbarBreadcrumb from "@/components/layout/navbar/NavbarBreadcrumb.vue"
import NavbarNotification from "@/components/layout/navbar/NavbarNotification.vue"
import NavbarProfile from "@/components/layout/navbar/NavbarProfile.vue"

export default {
    name: "TheNavBar",
    components: {
        iconButton,
        NavbarFleet,
        NavbarBreadcrumb,
        NavbarNotification,
        NavbarProfile,
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
            getSelectedFleet: state => state.fleets.selected,
        }),
        ...mapGetters({
            wsConnected: "websocket/wsConnected",
            user: "auth/user"
        }),
        fleetText() {
            return this.getSelectedFleet !== null ? this.getSelectedFleet.name : ""
        }
    },
    methods: {
        search: _debounce(
            function() {
                if (this.searchText.length > 0) {
                    this.doSearch()
                        .then(results => {
                            this.searchResults = results
                        })
                        .catch(error => {
                            this.searchResults.splice(0, this.searchResults.length);
                        })
                } else {
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

        handleSearchInputBlur(evt) {
            if (evt.relatedTarget?.classList.contains('list-group-item-action')) {
                setTimeout(() => { // hack to figure out a way to trigger the redirect before the list-group gets closed - or to switch to typeahead.
                    this.revealSearch = false
                }, 200);
            } else {
                this.revealSearch = false
            }
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

<style>
    .navbar .global-search {
        transition: width 0.25s ease-out;
    }
    .navbar .global-search:focus {
        width: 400px;
    }

    .btn-secondary.secondary-soft {
        color: rgba(0, 0, 0, 0.5) !important;
        background-color: #33333311 !important;
        border-color: #cccccc !important;
    }
    .btn-secondary.secondary-soft:hover {
        background-color: #33333322 !important;
        border-color: #999999 !important;
    }
</style>