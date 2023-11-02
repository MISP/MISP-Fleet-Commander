<template>
    <div class="d-flex container">
        <span v-for="entry in entries" :key="entry.id">
            <Avatar :avatar_id="entry.pinlist_id" width="32" height="32"></Avatar>
        </span>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import Avatar from "@/views/strategicView/elements/Avatar.vue";


export default {
    name: "ServerNodePinnedContent",
    components: {
        Avatar
    },
    props: {
        server: {
            type: Object,
            required: true
        }
    },
    computed: {
        ...mapGetters({
            pinnedEvents: "pinlists/pinnedEvents",
            pinnedSharingGroups: "pinlists/pinnedSharingGroups",
            pinnedByID: "pinlists/pinnedByID",
            entriesByServerID: "pinlists/entriesByServerID",
        }),
        entries() {
            return this.entriesByServerID[this.server.id]
        },
    },
}
</script>

<style scoped>
.container {
    min-height: 100px;
}

</style>