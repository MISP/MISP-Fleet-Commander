<template>
    <div class="">
        <template v-if="hasValidServerGroups">
            <b-dropdown-item
            href="#"
            v-for="(group, index) in getServerGroups"
            v-bind:key="index"
            @click="selectServerGroup(group)"
            >{{ group.name }}</b-dropdown-item>
        </template>
        <template v-else>
            <b-alert variant="danger text-nowrap" class="m-0" show >
                No server group available
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
            return this.getServerGroups.length > 0
        }
    },
    methods: {
        selectServerGroup(group) {
            this.$store.commit("serverGroups/selectServerGroup", group)
        },
        refreshServerGroupIndex() {
            this.refreshInProgress = true
            return new Promise((resolve, reject) => {
                this.$store.dispatch("serverGroups/initFetch")
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        this.$bvToast.toast(error, {
                            title: "Could not fetch server group index",
                            variant: "danger",
                        })
                        reject()
                    })
                    .finally(() => {
                        this.refreshInProgress = false
                    })
            })
        },
        mounted() {
            this.refreshServerGroupIndex()
        }
    }
}
</script>

<style scoped>

</style>