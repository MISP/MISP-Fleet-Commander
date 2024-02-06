<template>
    <span class="avatar-container">
        <span
            v-if="pinlist_model == 'event'"
            class="m-1 event-avatar"
        >
            <AvatarImage v-bind="$attrs" :avatar_id="pinlist_id"></AvatarImage>
        </span>
        <span
            v-else-if="pinlist_model == 'attribute'"
            class="m-1 attribute-avatar"
        >
            <AvatarImage v-bind="$attrs" :avatar_id="pinlist_id"></AvatarImage>
        </span>
        <span
            v-else-if="pinlist_model == 'sharinggroup'"
            class="m-1 sharinggroup-avatar"
        >
            <AvatarImage v-bind="$attrs" :avatar_id="pinlist_id"></AvatarImage>
        </span>
        <span
            v-else-if="pinlist_model == 'sighting'"
            class="m-1 sighting-avatar"
        >
            <AvatarImage v-bind="$attrs" :avatar_id="pinlist_id"></AvatarImage>
        </span>
        <span
            v-else-if="pinlist_model == 'analystdata'"
            class="m-1 analystdata-avatar"
        >
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


.attribute-avatar {
    display: inline-block;
    box-shadow: 0 0 4px 0 #00000077;
    border-radius: 50%;
    overflow: hidden;
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
.analystdata-avatar {
    display: inline-block;
    border: 1px solid #c8da00;
    box-shadow: 0 0 4px 0 #bbc54f;
}

</style>