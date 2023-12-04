<template>
    <div class="">
        <template v-if="hasValidFleets">
            <b-dropdown-item
            href="#"
            v-for="(fleet, index) in getFleets"
            v-bind:key="index"
            @click="selectFleet(fleet)"
            :active="getSelectedFleet && getSelectedFleet.id == fleet.id"
            >{{ fleet.name }}</b-dropdown-item>
        </template>
        <template v-else>
            <b-alert variant="danger text-nowrap" class="m-0" show >
                No fleet available
            </b-alert>
        </template>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"

export default {
    name: "NavbarFleet",
    components: {
    },
    data: function () {
        return {
        }
    },
    computed: {
        ...mapState({
            getSelectedFleet: state => state.fleets.selected,
            getFleets: state => state.fleets.all
        }),
        hasValidFleets() {
            return Object.values(this.getFleets).length > 0
        }
    },
    methods: {
        selectFleet(fleet) {
            this.$store.dispatch("fleets/selectFleet", { data: fleet, redirect: true })
        },
        refreshFleetIndex() {
            this.refreshInProgress = true
            return new Promise((resolve, reject) => {
                this.$store.dispatch("fleets/initFetch", {use_cache: true})
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        this.$bvToast.toast(error, {
                            title: "Could not fetch fleet index",
                            variant: "danger",
                        })
                        reject()
                    })
                    .finally(() => {
                        this.refreshInProgress = false
                    })
            })
        },
    },
    mounted() {
        // this.refreshFleetIndex()
    }
}
</script>

<style scoped>

</style>