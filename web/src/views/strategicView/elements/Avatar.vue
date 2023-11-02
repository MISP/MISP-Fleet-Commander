<template>
    <span>
        <img
            :src="`${avatarURL}/${avatar_id}.png`"
            v-bind="$attrs"
            class="" alt="Entry avatar"
        >
    </span>
</template>

<script>
import pinlistsApi from "@/api/pinLists"


export default {
    name: "Avatar",
    inheritAttrs: false,
    props: {
        avatar_id: {
            type: Number,
            required: true,
        }
    },
    data: function () {
        return {}
    },
    computed: {
        avatarURL() {
            const url = pinlistsApi.avatarURL()
            return url
        }
    },
    methods: {
    },
}
</script>

<style scoped>

</style>