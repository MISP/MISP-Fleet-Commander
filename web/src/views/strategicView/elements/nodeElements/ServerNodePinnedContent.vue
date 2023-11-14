<template>
    <div class="d-flex flex-column container">
        <div class="text-muted">
            <i class="fa fa-envelope fa-fw"></i> Events
        </div>
        <div>
            <span v-for="entry in events" :key="entry.id">
                <Avatar :avatar_id="entry.pinlist_id" :pinlist_model="entry.model" width="32" height="32"></Avatar>
            </span>
        </div>
        <div class="text-muted mt-1">
            <i class="fa fa-users fa-fw"></i> Sharing Groups
        </div>
        <div>
            <span v-for="entry in sharinggroups" :key="entry.id">
                <Avatar :avatar_id="entry.pinlist_id" :pinlist_model="entry.model" width="32" height="32"></Avatar>
            </span>
        </div>
        <div class="text-muted mt-1">
            <i class="fa fa-eye fa-fw"></i> Sightings
        </div>
        <div>
            <span v-for="entry in sightings" :key="entry.id">
                <Avatar :avatar_id="entry.pinlist_id" :pinlist_model="entry.model" width="32" height="32"></Avatar>
            </span>
        </div>
    </div>
</template>

<script>
import { mapGetters } from "vuex"
import Avatar from "@/views/strategicView/elements/avatar/Avatar.vue";


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
            entriesByServerID: "pinlists/entriesByServerID",
            pinnedByID: "pinlists/pinnedByID",
        }),
        entries() {
            let tmp =  this.entriesByServerID[this.server.id] || []
            tmp.map(e => {
                e.model = this.pinnedByID[e.pinlist_id].model
                return e
            })
            return tmp
        },
        events() {
            return this.entries.filter(e => e.model == 'event')
        },
        sharinggroups() {
            return this.entries.filter(e => e.model == 'sharinggroup')
        },
        sightings() {
            return this.entries.filter(e => e.model == 'sighting')
        }
    },
}
</script>

<style scoped>
.container {
    min-height: 180px;
}

</style>