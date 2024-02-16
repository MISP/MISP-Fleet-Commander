<template>
    <div class="d-flex flex-column container">
        <div class="text-muted">
            <i class="fa fa-envelope fa-fw"></i> Events: {{ events.length }}
        </div>
        <div>
            <span v-for="entry in events" :key="entry.id">
                <AvatarActions :server_id="server.id" :pinlist_id="entry.pinlist_id" :pinlist_model="entry.model" width="32" height="32"></AvatarActions>
            </span>
        </div>
        <div class="text-muted">
            <i class="fa fa-cube fa-fw"></i> Attributes: {{ attributes.length }}
        </div>
        <div>
            <span v-for="entry in attributes" :key="entry.id">
                <AvatarActions :server_id="server.id" :pinlist_id="entry.pinlist_id" :pinlist_model="entry.model" width="32" height="32"></AvatarActions>
            </span>
        </div>
        <div class="text-muted mt-1">
            <i class="fa fa-users fa-fw"></i> Sharing Groups: {{ sharinggroups.length }}
        </div>
        <div>
            <span v-for="entry in sharinggroups" :key="entry.id">
                <AvatarActions :server_id="server.id" :pinlist_id="entry.pinlist_id" :pinlist_model="entry.model" width="32" height="32"></AvatarActions>
            </span>
        </div>
        <div class="text-muted mt-1">
            <i class="fa fa-eye fa-fw"></i> Sightings: {{ sightings.length }}
        </div>
        <div>
            <span v-for="entry in sightings" :key="entry.id">
                <AvatarActions :server_id="server.id" :pinlist_id="entry.pinlist_id" :pinlist_model="entry.model" width="32" height="32"></AvatarActions>
            </span>
        </div>
        <div class="text-muted mt-1">
            <i class="fa fa-sticky-note fa-fw"></i> Analyst Data: {{ analystdata.length }}
        </div>
        <div>
            <span v-for="entry in analystdata" :key="entry.id">
                <AvatarActions :server_id="server.id" :pinlist_id="entry.pinlist_id" :pinlist_model="entry.model" width="32" height="32"></AvatarActions>
            </span>
        </div>
    </div>
</template>

<script>
import { mapGetters } from "vuex"
import AvatarActions from "@/views/strategicView/elements/avatar/AvatarActions.vue";


export default {
    name: "ServerNodePinnedContent",
    components: {
        AvatarActions
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
        attributes() {
            return this.entries.filter(e => e.model == 'attribute')
        },
        sharinggroups() {
            return this.entries.filter(e => e.model == 'sharinggroup')
        },
        sightings() {
            return this.entries.filter(e => e.model == 'sighting')
        },
        analystdata() {
            return this.entries.filter(e => e.model == 'analystdata')
        },
    },
}
</script>

<style scoped>
.container {
    min-height: 180px;
}

</style>