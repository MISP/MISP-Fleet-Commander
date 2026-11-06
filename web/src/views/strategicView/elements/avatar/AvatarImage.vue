<template>
    <span>
        <img
            :src="src || placeholder"
            v-bind="$attrs"
            class="" alt="Entry avatar"
        >
    </span>
</template>

<script>
import common from "@/api/common"
import pinlistsApi from "@/api/pinLists"

// Transparent pixel keeping the layout in place until the avatar is fetched
const PLACEHOLDER = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

// An entry's avatar never changes: fetch it once per page and share it between the components showing it
const avatars = new Map()

function avatarObjectURL(avatarID) {
    if (!avatars.has(avatarID)) {
        const request = common.fetchImageObjectURL(`${pinlistsApi.avatarURL()}/${avatarID}.png`)
            .catch((error) => {
                avatars.delete(avatarID)
                throw error
            })
        avatars.set(avatarID, request)
    }
    return avatars.get(avatarID)
}

export default {
    name: "AvatarImage",
    inheritAttrs: false,
    props: {
        avatar_id: {
            type: Number,
            required: true,
        }
    },
    data: function () {
        return {
            src: null,
            placeholder: PLACEHOLDER,
        }
    },
    watch: {
        avatar_id: {
            immediate: true,
            handler(avatarID) {
                this.src = null
                avatarObjectURL(avatarID)
                    .then((objectURL) => {
                        if (avatarID === this.avatar_id) {
                            this.src = objectURL
                        }
                    })
                    .catch(() => {})
            },
        },
    },
}
</script>

<style scoped>

</style>
