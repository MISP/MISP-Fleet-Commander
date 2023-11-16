<template>
    <b-overlay :show="show" rounded="sm" :spinner-small="true" class="d-inline-block">
        <span class="avatar-container">
            <Avatar
                v-bind="$attrs"
                :pinlist_id="pinlist_id"
                :pinlist_model="pinlist_model"
            ></Avatar>
            <span
                role="button" tabindex="0" class="delete-entry text-center"
                title="Delete this entry from this server"
                @click="deleteFromServer()"
            >×</span>
        </span>
    </b-overlay>
</template>

<script>
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
    },
    methods: {
        deleteFromServer() {
            this.show = true
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
        }
    },
}
</script>

<style scoped>

.avatar-container {
    position: relative;
    display: inline-block;
}

.delete-entry {
    display: none;
}

.avatar-container:hover .delete-entry {
    display: inline-block;
    box-sizing: content-box;
    width: 9px;
    height: 9px;
    line-height: 9px;
    font-size: 9px;
    position: absolute;
    top: -2px;
    right: -2px;
    border-radius: 50%;
    border: 2px solid #fff;
    color: #fff;
    background: #da4e49;
}

</style>