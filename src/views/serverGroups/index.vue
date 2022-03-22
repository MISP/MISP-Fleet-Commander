<template>
    <div>
        <div class="d-flex align-items-center pb-1">
            <h4>Server Groups</h4>
            <b-button
                class="ml-auto"
                size="sm"
                variant="primary"
                v-b-modal.modal-add
            >
                <iconButton text="New group" icon="plus"></iconButton>
            </b-button>
        </div>

        <b-list-group>
            <b-list-group-item
                v-for="(group, index) in getServerGroups"
                v-bind:key="index"
                href="#" class="p-2 flex-column align-items-start"
                :active="getSelectedServerGroupId == group.id"
                @click="selectServerGroup(group)"
            >
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">{{ group.name }}</h5>
                    <small>{{ group.server_count }} {{ group.server_count > 1 ? "servers" : "server"}}</small>
                </div>
                <p class="mb-1">{{ group.description }}</p>
            </b-list-group-item>
        </b-list-group>

        <b-alert :show="serverGroupEmpty" variant="primary">
            There are no server group available. Create one to get started!
        </b-alert>

        <AddModal
            :groupForm="groupData"
            @addition-success="handleAdd"
        ></AddModal>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import iconButton from "@/components/ui/elements/iconButton.vue"
import AddModal from "@/views/serverGroups/AddModal.vue"
import router from "@/router"

export default {
    name: "ServerGroup",
    components: {
        iconButton,
        AddModal
    },
    data: function () {
        return {
            refreshInProgress: false,
            groupData: {}
        }
    },
    computed: {
        ...mapState({
            getSelectedServerGroup: state => state.serverGroups.selected,
            getServerGroups: state => state.serverGroups.all
        }),
        ...mapGetters({
            serverGroupCount: "serverGroups/serverGroupCount"
        }),
        getSelectedServerGroupId () {
            return this.getSelectedServerGroup === null ? -1 : this.getSelectedServerGroup.id
        },
        serverGroupEmpty() {
            return this.serverGroupCount == 0
        }
    },
    methods: {
        selectServerGroup(group) {
            this.$store.dispatch("serverGroups/selectServerGroup", group)
            router.push({ path: '/servers/' })
        },
        handleAdd() {
            this.refreshServerGroupIndex()
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
    },
    mounted() {
        this.refreshServerGroupIndex()
    }
}
</script>

<style scoped>
</style>
