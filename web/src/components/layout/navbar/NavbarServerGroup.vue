<template>
    <div class="">
        <template v-if="hasValidServerGroups">
            <b-dropdown-item
            href="#"
            v-for="(group, index) in getServerGroups"
            v-bind:key="index"
            @click="selectServerGroup(group)"
            :active="getSelectedServerGroup && getSelectedServerGroup.id == group.id"
            >{{ group.name }}</b-dropdown-item>
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
    name: "NavbarServerGroup",
    components: {
    },
    data: function () {
        return {
        }
    },
    computed: {
        ...mapState({
            getSelectedServerGroup: state => state.serverGroups.selected,
            getServerGroups: state => state.serverGroups.all
        }),
        hasValidServerGroups() {
            return Object.values(this.getServerGroups).length > 0
        }
    },
    methods: {
        selectServerGroup(group) {
            this.$store.dispatch("serverGroups/selectServerGroup", { data: group, redirect: true })
        },
        refreshServerGroupIndex() {
            this.refreshInProgress = true
            return new Promise((resolve, reject) => {
                this.$store.dispatch("serverGroups/initFetch", {use_cache: true})
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
        // this.refreshServerGroupIndex()
    }
}
</script>

<style scoped>

</style>