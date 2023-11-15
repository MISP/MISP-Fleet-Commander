<template>
    <div>
        <div class="d-flex align-items-center pb-1">
            <h4><i class="fas fa-layer-group mr-2"></i>Fleets</h4>
            <b-button
                class="ml-auto"
                size="sm"
                variant="primary"
                v-b-modal.modal-add
            >
                <iconButton text="New fleet" icon="plus"></iconButton>
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
                <div class="d-flex">
                    <span>{{ group.description }}</span>
                    <span class="ml-auto">
                        <b-button
                            class="ml-auto fa fa-trash reveal-on-parent-hover"
                            size="sm"
                            variant="outline-danger"
                            v-b-modal.modal-delete-selected
                            @click.stop="selectGroupForDeletion(group.id)"
                        >
                        </b-button>
                    </span>
                </div>
            </b-list-group-item>
        </b-list-group>

        <b-alert :show="serverGroupEmpty" variant="primary">
            <strong>No fleet available.</strong> Create one to get started!
        </b-alert>

        <AddModal
            :groupForm="groupData"
            @addition-success="handleAdd"
        ></AddModal>
        <DeleteModal
            :group_id="group_id_to_delete"
            @deletion-success="handleDelete"
        ></DeleteModal>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import iconButton from "@/components/ui/elements/iconButton.vue"
import AddModal from "@/views/serverGroups/AddModal.vue"
import DeleteModal from "@/views/serverGroups/DeleteModal.vue"
import router from "@/router"

export default {
    name: "ServerGroup",
    components: {
        iconButton,
        AddModal,
        DeleteModal,
    },
    data: function () {
        return {
            refreshInProgress: false,
            groupData: {},
            group_id_to_delete: -1,
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
            this.$store.dispatch("serverGroups/selectServerGroup", { data: group, redirect: true })
        },
        selectGroupForDeletion(group_id) {
            this.group_id_to_delete = group_id
        },
        handleAdd() {
            this.refreshServerGroupIndex()
        },
        handleDelete() {
        },
        refreshServerGroupIndex() {
            this.refreshInProgress = true
            return new Promise((resolve, reject) => {
                this.$store.dispatch("serverGroups/initFetch", {use_cache: false})
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
        this.refreshServerGroupIndex()
    }
}
</script>

<style scoped>
button.reveal-on-parent-hover {
    visibility: hidden;
}

.list-group-item:hover .reveal-on-parent-hover {
    visibility: visible;
}
</style>
