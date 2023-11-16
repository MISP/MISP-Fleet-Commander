<template>
    <span class="avatar-container">
        <span class="m-1 event-avatar" v-if="pinlist_model == 'event'">
            <AvatarImage v-bind="$attrs" :avatar_id="pinlist_id"></AvatarImage>
        </span>
        <span class="m-1 sharinggroup-avatar" v-else-if="pinlist_model == 'sharinggroup'">
            <AvatarImage v-bind="$attrs" :avatar_id="pinlist_id"></AvatarImage>
        </span>
        <span class="m-1 sighting-avatar" v-else-if="pinlist_model == 'sighting'">
            <AvatarImage v-bind="$attrs" :avatar_id="pinlist_id"></AvatarImage>
        </span>
    </span>
</template>

<script>
import AvatarImage from "@/views/strategicView/elements/avatar/AvatarImage.vue"


export default {
    name: "Avatar",
    inheritAttrs: false,
    components: {
        AvatarImage
    },
    props: {
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
        }
    },
    computed: {
    },
    methods: {
    },
}
</script>

<style scoped>
.event-avatar {
    display: inline-block;
    box-shadow: 0 0 4px 0 #00000077;
}

.sharinggroup-avatar {
    display: inline-block;
    border: 2px solid #2a009d;
}

.sighting-avatar {
    display: inline-block;
    border: 1px solid #00000066;
    border-radius: 50%;
    overflow: hidden;
}

</style>