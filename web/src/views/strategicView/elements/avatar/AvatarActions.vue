<template>
    <b-overlay :show="show" rounded="sm" :spinner-small="true" class="d-inline-block">
        <span class="avatar-container">
            <Avatar
                v-bind="$attrs"
                :pinlist_id="pinlist_id"
                :pinlist_model="pinlist_model"
            ></Avatar>
            <div class="action-container flex-row-reverse">
                <span
                    role="button" tabindex="0"
                    class="action-entry delete-entry text-center"
                    title="Delete this entry from this server"
                    @click.stop="deleteFromServer(pinlist_id)"
                >
                    <i class="fas fa-fw fa-times"></i>
                </span>
                <span
                    v-if="pinlist_model == 'event'"
                    role="button" tabindex="0"
                    class="action-entry publish-event text-center"
                    title="Publish this event"
                    @click.stop="publishEvent(pinlist_id)"
                >
                    <i class="fas fa-fw fa-upload"></i>
                </span>
            </div>
        </span>
    </b-overlay>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import Avatar from "@/views/strategicView/elements/avatar/Avatar.vue"


export default {
    name: "AvatarActions",
    inheritAttrs: false,
    components: {
        Avatar
    },
    props: {
        server_id: {
            type: Number,
            required: true,
        },
        pinlist_id: {
            type: Number,
            required: true,
        },
        pinlist_model: {
            type: String,
            required: true,
        },
    },
    data: function () {
        return {
            show: false,
        }
    },
    computed: {
        ...mapGetters({
            pinnedByID: "pinlists/pinnedByID",
        }),
    },
    methods: {
        deleteFromServer(entry_id) {
            this.show = true
            const entry = this.pinnedByID[entry_id]
            this.$bvModal.msgBoxConfirm(`Please confirm that you want to remove the data associated to the entry ${entry.uuid} from that server.`, {
                title: 'Please Confirm',
                size: 'sm',
                buttonSize: 'sm',
                okVariant: 'danger',
                okTitle: 'Yes',
                cancelTitle: 'No',
                footerClass: 'p-2',
                hideHeaderClose: false,
            }).then(confirm => {
                if (!confirm) {
                    this.show = false
                    return
                }
                this.$store.dispatch("pinlists/deleteFromServer", {entry_id: this.pinlist_id, server_id: this.server_id})
                    .catch(error => {
                        this.$bvToast.toast(error.message, {
                            title: 'Error while trying to delete the entry from the server',
                            variant: "danger",
                        })
                    })
                    .finally(() => {
                        this.show = false
                    })
            })
        },
        publishEvent(entry_id) {
            this.show = true
            this.$bvModal.msgBoxConfirm(`Please confirm that you want to publish that event`, {
                title: 'Please Confirm',
                size: 'sm',
                buttonSize: 'sm',
                okVariant: 'success',
                okTitle: 'Yes',
                cancelTitle: 'No',
                footerClass: 'p-2',
                hideHeaderClose: false,
            }).then(confirm => {
                if (!confirm) {
                    this.show = false
                    return
                }
                this.$store.dispatch("pinlists/publishEventOnServer", {entry_id: this.pinlist_id, server_id: this.server_id})
                    .catch(error => {
                        this.$bvToast.toast(error.message, {
                            title: 'Error while trying to delete the entry from the server',
                            variant: "danger",
                        })
                    })
                    .finally(() => {
                        this.show = false
                    })
            })
        }
    },
}
</script>

<style scoped>

.avatar-container {
    position: relative;
    display: inline-block;
}

.action-container {
    display: none;
    position: absolute;
    top: -2px;
    right: -2px;
}

.avatar-container:hover .action-container {
    display: flex;
}

.action-entry {
    display: flex;
    justify-content: center;
    align-items: center;
    box-sizing: content-box;
    width: 9px;
    height: 9px;
    line-height: 10px;
    font-size: 6px;
    border-radius: 50%;
    margin-top: 2px;
}

.delete-entry {
    border: 2px solid #fff;
    color: #fff;
    background: #da4e49;
}

.publish-event {
    border: 2px solid #fff;
    color: #fff;
    background: #303ea8;
}

</style>